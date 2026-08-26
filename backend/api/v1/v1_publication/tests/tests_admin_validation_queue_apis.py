from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import (
    DroughtCategory,
    PublicationStatus,
    ValidationStatus,
    is_validated,
)
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.validation.utils import (
    build_validation_stats,
    consensus,
    progress_reviews,
    reviewers_required,
    row_status,
)
from api.v1.v1_users.constants import TechnicalWorkingGroup, UserRoleTypes
from api.v1.v1_users.models import SystemUser


class ConsensusTestCase(APITestCase):
    """D-8: distance-aware, outlier-robust, bounded [0, 100]."""

    def test_known_spreads(self):
        cases = {
            (3, 3, 3): 100,          # unanimous
            (3, 3, 2): 87,           # one reviewer one step off
            (1, 2): 80,              # adjacent classes
            (1, 5): 20,              # Normal vs D4 — the case worth flagging
            (1, 1, 1, 1, 5): 68,     # single outlier against four agreeing
            (5, 2, 1, 4): 40,        # genuinely scattered
            (0, 0, 5, 5): 0,         # maximally split — the exact floor
            (3, 3): 100,             # two reviewers, agreeing
        }
        for categories, expected in cases.items():
            self.assertEqual(
                consensus(list(categories)), expected, msg=str(categories)
            )

    def test_no_submissions_is_none_not_zero(self):
        self.assertIsNone(consensus([]))

    def test_one_submission_is_none_not_unanimous(self):
        """D-9: 100% is a claim about agreement between people.

        This used to return 100, which made a publication assigned a single
        reviewer report full agreement on every Inkhundla — and made any row
        still waiting on four other TWGs look settled.
        """
        self.assertIsNone(consensus([3]))

    def test_never_leaves_bounds(self):
        """Exhaustive over every multiset of D-classes up to 5 submissions."""
        from itertools import combinations_with_replacement

        scale = range(DroughtCategory.normal, DroughtCategory.d4 + 1)
        for size in range(1, 6):
            for combo in combinations_with_replacement(scale, size):
                value = consensus(list(combo))
                if value is None:      # below two submissions — see D-9
                    self.assertLess(len(combo), 2, msg=str(combo))
                    continue
                self.assertGreaterEqual(value, 0, msg=str(combo))
                self.assertLessEqual(value, 100, msg=str(combo))

    def test_distance_aware_beats_modal_share(self):
        """[1,2] and [1,5] are both a 50% modal share — not the same thing."""
        self.assertGreater(consensus([1, 2]), consensus([1, 5]))


class IsValidatedTestCase(APITestCase):
    """D-11: No Data is not a validation outcome."""

    def test_predicate(self):
        self.assertFalse(is_validated(None))
        self.assertFalse(is_validated(DroughtCategory.none))
        # Normal is a real class — an off-by-one here would silently block
        # every wet Inkhundla from ever being publishable.
        self.assertTrue(is_validated(DroughtCategory.normal))
        self.assertTrue(is_validated(DroughtCategory.d4))

    def test_no_data_never_reads_as_validated(self):
        """It falls through to the actionable queue, not out of it."""
        self.assertEqual(
            row_status(DroughtCategory.none, covered=5, required=5),
            ValidationStatus.ready,
        )
        self.assertEqual(
            row_status(DroughtCategory.none, covered=1, required=5),
            ValidationStatus.awaiting,
        )

    def test_validated_takes_precedence_over_coverage(self):
        """A decided Inkhundla is not shown as outstanding work (D-10)."""
        self.assertEqual(
            row_status(DroughtCategory.d2, covered=2, required=5),
            ValidationStatus.validated,
        )


class DisagreementCardTestCase(APITestCase):
    """Summary card 2: "more than 3 different drought scores assigned".

    The boundary is the whole point — `> 3`, so exactly three distinct classes
    must NOT qualify. An off-by-one here silently changes the headline number
    the admin triages by.
    """

    def _disagreement(self, spreads):
        rows = [
            {"status": ValidationStatus.ready, "dclass_spread": spread}
            for spread in spreads
        ]
        cards = {c["key"]: c["value"] for c in build_validation_stats(rows)}
        return cards["disagreement"]

    def test_four_distinct_classes_qualifies(self):
        self.assertEqual(self._disagreement([[0, 1, 2, 3]]), 1)

    def test_exactly_three_distinct_classes_does_not(self):
        self.assertEqual(self._disagreement([[1, 2, 3]]), 0)

    def test_repeats_do_not_inflate_the_count(self):
        """Six submissions, three distinct classes — still not disagreement."""
        self.assertEqual(self._disagreement([[1, 1, 2, 2, 3, 3]]), 0)
        self.assertEqual(self._disagreement([[2, 2, 2, 2, 2]]), 0)

    def test_counts_rows_not_classes(self):
        self.assertEqual(
            self._disagreement([[0, 1, 2, 3], [0, 1, 2, 3, 4], [1, 2]]), 2
        )

    def test_empty_spread_is_not_disagreement(self):
        self.assertEqual(self._disagreement([[]]), 0)


@override_settings(USE_TZ=False, TEST_ENV=True)
class ValidationQueueAPIsTestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

        self.publication = Publication.objects.first()
        self.total = len(self.publication.initial_values)
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.reviewer = SystemUser.objects.get(
            pk=self.publication.reviews.first().user_id
        )
        self.client.force_authenticate(user=self.admin)

        def url(name):
            return reverse(
                name,
                kwargs={"version": "v1", "pk": self.publication.id},
            )

        self.stats_url = url("validation-queue-stats")
        self.table_url = url("validation-queue-administrations")

    def _rows(self, **params):
        res = self.client.get(self.table_url, params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return res.data["data"]

    # ---- routing ---------------------------------------------------------
    def test_routes_are_not_swallowed_by_publication_details(self):
        """D-3: /admin/publication/{pk} is un-anchored; these must not match
        it, which would 200 with a publication body instead of queue data."""
        for url in (self.stats_url, self.table_url):
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertNotIn("cdi_geonode_id", res.data)

    # ---- stats -----------------------------------------------------------
    def test_stats_shape_and_cards(self):
        res = self.client.get(self.stats_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(set(res.data), {"meta", "data"})
        self.assertEqual(
            [card["key"] for card in res.data["data"]],
            ["ready", "disagreement", "validated", "awaiting"],
        )
        self.assertEqual(
            set(res.data["meta"]),
            {
                "publication_id", "year_month", "published_at", "total",
                "reviewers_required", "can_publish", "pending_validation",
                "narrative", "bulletin_url", "sector_context",
            },
        )

    def test_meta_carries_the_current_narrative(self):
        """Re-opening the publish modal must edit the live description, not
        blank it — the page has no other source for it."""
        text = "Conditions eased across the Lowveld."
        self.publication.narrative = text
        self.publication.save()
        meta = self.client.get(self.stats_url).data["meta"]
        self.assertEqual(meta["narrative"], text)

    def test_meta_carries_the_current_sector_context(self):
        """Same trap again, one field wider: the modal submits the whole
        sector map on every update, so without it here the admin reopens to
        eight empty boxes and has to retype what is already published."""
        context = {"1": "Seed distribution continues.", "3": "Boreholes."}
        self.publication.sector_context = context
        self.publication.save()
        meta = self.client.get(self.stats_url).data["meta"]
        self.assertEqual(meta["sector_context"], context)

    def test_meta_sector_context_is_null_when_never_written(self):
        meta = self.client.get(self.stats_url).data["meta"]
        self.assertIsNone(meta["sector_context"])

    def test_meta_carries_the_current_bulletin_url(self):
        """Same trap as the narrative: the modal submits the bulletin URL on
        every update, so a field it cannot prefill is a field it wipes."""
        url = "https://ndma.org.sz/bulletin-2026-05.pdf"
        self.publication.bulletin_url = url
        self.publication.save()
        meta = self.client.get(self.stats_url).data["meta"]
        self.assertEqual(meta["bulletin_url"], url)

    def test_status_counts_partition_the_queue(self):
        """D-10: ready + awaiting + validated == total. `disagreement`
        cross-cuts all three and is deliberately not part of the sum."""
        cards = {c["key"]: c["value"] for c in
                 self.client.get(self.stats_url).data["data"]}
        self.assertEqual(
            cards["ready"] + cards["awaiting"] + cards["validated"],
            self.total,
        )

    def test_cards_match_their_tabs(self):
        """Each card's number is the row count behind its matching tab."""
        cards = {c["key"]: c["value"] for c in
                 self.client.get(self.stats_url).data["data"]}
        for key in ValidationStatus.FieldStr:
            res = self.client.get(self.table_url, {"status": key})
            self.assertEqual(res.data["total"], cards[key], msg=key)

    # ---- publish gate ----------------------------------------------------
    def test_can_publish_false_until_every_inkhundla_is_validated(self):
        self.publication.validated_values = None
        self.publication.save()
        meta = self.client.get(self.stats_url).data["meta"]
        self.assertFalse(meta["can_publish"])
        self.assertEqual(meta["pending_validation"], self.total)

        self.publication.validated_values = [
            {"administration_id": v["administration_id"],
             "category": DroughtCategory.d2}
            for v in self.publication.initial_values
        ]
        self.publication.save()
        meta = self.client.get(self.stats_url).data["meta"]
        self.assertTrue(meta["can_publish"])
        self.assertEqual(meta["pending_validation"], 0)

    def test_no_data_blocks_publishing(self):
        """D-11 across the gate: every Inkhundla has a category, but one of
        them is -9999, so the publication is not publishable."""
        values = [
            {"administration_id": v["administration_id"],
             "category": DroughtCategory.d2}
            for v in self.publication.initial_values
        ]
        values[0]["category"] = DroughtCategory.none
        self.publication.validated_values = values
        self.publication.save()

        meta = self.client.get(self.stats_url).data["meta"]
        self.assertFalse(meta["can_publish"])
        self.assertEqual(meta["pending_validation"], 1)

        # ... and the row is back in the actionable queue, not "validated".
        row = next(
            r for r in self._rows()
            if r["administration_id"] == values[0]["administration_id"]
        )
        self.assertNotEqual(row["status"], ValidationStatus.validated)
        self.assertIsNone(row["validated_category"])

        # ... and the write path agrees with the button.
        res = self.client.put(
            reverse(
                "publication-details",
                kwargs={"version": "v1", "pk": self.publication.id},
            ),
            {"status": PublicationStatus.published},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publish_succeeds_once_all_validated(self):
        self.publication.validated_values = [
            {"administration_id": v["administration_id"],
             "category": DroughtCategory.d1}
            for v in self.publication.initial_values
        ]
        self.publication.save()
        res = self.client.put(
            reverse(
                "publication-details",
                kwargs={"version": "v1", "pk": self.publication.id},
            ),
            {
                "status": PublicationStatus.published,
                "narrative": "Conditions eased across the Lowveld.",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, PublicationStatus.published)
        self.assertEqual(
            self.publication.narrative,
            "Conditions eased across the Lowveld.",
        )

    # ---- table -----------------------------------------------------------
    def test_row_shape_matches_the_frontend_contract(self):
        row = self._rows()[0]
        self.assertEqual(
            set(row),
            {
                "administration_id", "label", "group", "zone",
                "reviews_completed", "reviews_total", "reviewers",
                "dclass_spread", "consensus", "confidence",
                "confidence_band", "status", "awaiting_count",
                "validated_category",
            },
        )
        # No private or admin-only field survives into the response.
        self.assertNotIn("submissions", row)
        self.assertNotIn("_distinct_classes", row)

    def test_reviewer_views_of_the_same_list_stay_consistent(self):
        """len(reviewers) == len(dclass_spread), and reviews_completed counts
        TWGs — so it can be smaller, never larger (D-2, D-12)."""
        for row in self._rows():
            self.assertEqual(
                len(row["reviewers"]), len(row["dclass_spread"])
            )
            self.assertLessEqual(
                row["reviews_completed"], len(row["reviewers"]) or 0
            )

    def test_progress_never_exceeds_one_hundred_percent(self):
        """Both sides of the fraction are TWG-based: 6 submissions across 4
        TWGs must read 4/4, never 6/4 (D-2)."""
        for row in self._rows():
            self.assertLessEqual(
                row["reviews_completed"], row["reviews_total"]
            )

    def test_rows_are_ordered_by_administration_name(self):
        """D-7: pagination and the decision page's prev/next both depend on a
        defined order; build_rows iterates initial_values in JSON order."""
        labels = [r["label"] for r in self._rows(page_size=100)]
        self.assertEqual(labels, sorted(labels, key=lambda s: s.lower()))

    def test_search_spans_the_whole_publication_not_just_page_one(self):
        target = self._rows(page_size=100)[-1]["label"]
        rows = self._rows(search=target.lower())
        self.assertTrue(rows)
        self.assertTrue(
            all(target.lower() in r["label"].lower() for r in rows)
        )

    def test_status_filter_returns_only_that_status(self):
        for key in ValidationStatus.FieldStr:
            for row in self._rows(status=key, page_size=100):
                self.assertEqual(row["status"], key)

    def test_pagination_reports_the_server_total(self):
        res = self.client.get(self.table_url, {"page_size": 2})
        self.assertEqual(res.data["total"], self.total)
        self.assertLessEqual(len(res.data["data"]), 2)

    def test_unknown_status_is_rejected(self):
        res = self.client.get(self.table_url, {"status": "nonsense"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disagreement_card_reflects_real_reviews(self):
        """End-to-end: four reviewers choosing four different D-classes on one
        Inkhundla makes the card read 1 (D-8 filters None/-9999 first)."""
        reviews = list(self.publication.reviews.all()[:4])
        if len(reviews) < 4:
            self.skipTest("fixture needs 4 reviewers")
        administration_id = self.publication.initial_values[0][
            "administration_id"
        ]
        distinct = [
            DroughtCategory.normal,
            DroughtCategory.d1,
            DroughtCategory.d2,
            DroughtCategory.d4,
        ]
        for review, category in zip(reviews, distinct):
            review.suggestion_values = [{
                "administration_id": administration_id,
                "category": category,
                "reviewed": True,
            }]
            review.save()

        cards = {c["key"]: c["value"] for c in
                 self.client.get(self.stats_url).data["data"]}
        self.assertEqual(cards["disagreement"], 1)

        row = next(
            r for r in self._rows(page_size=100)
            if r["administration_id"] == administration_id
        )
        self.assertEqual(sorted(row["dclass_spread"]), sorted(distinct))

    def test_no_data_submissions_are_excluded_from_the_spread(self):
        """-9999 is not a point on the scale: it must not reach dclass_spread,
        consensus, or the distinct-class count (D-8)."""
        review = self.publication.reviews.first()
        administration_id = self.publication.initial_values[0][
            "administration_id"
        ]
        review.suggestion_values = [{
            "administration_id": administration_id,
            "category": DroughtCategory.none,
            "reviewed": True,
        }]
        review.save()

        row = next(
            r for r in self._rows(page_size=100)
            if r["administration_id"] == administration_id
        )
        self.assertEqual(row["dclass_spread"], [])
        self.assertIsNone(row["consensus"])

    # ---- reviewers_required ---------------------------------------------
    def test_reviewers_required_counts_twgs_not_people(self):
        """D-2: N reviewers sharing one TWG require one, not N.

        Five MoAg reviewers must not satisfy a threshold designed for
        cross-institutional agreement.
        """
        reviews = list(self.publication.reviews.all())
        self.assertGreater(len(reviews), 1, "fixture needs >1 reviewer")
        for review in reviews:
            review.user.technical_working_group = TechnicalWorkingGroup.met
            review.user.save()
        self.assertEqual(reviewers_required(self.publication), 1)

    def test_reviewers_required_counts_distinct_twgs(self):
        """Two TWGs across many reviewers require two."""
        reviews = list(self.publication.reviews.all())
        for index, review in enumerate(reviews):
            review.user.technical_working_group = (
                TechnicalWorkingGroup.met if index % 2
                else TechnicalWorkingGroup.dwa
            )
            review.user.save()
        expected = 2 if len(reviews) > 1 else 1
        self.assertEqual(reviewers_required(self.publication), expected)

    def test_progress_reviews_denominator_is_assigned_twgs(self):
        """The denominator is who was asked, not the size of the TWG enum.

        Two TWGs assigned and both submitted reads 2/2 — it used to read 2/5
        and never reach completion, because three TWGs that were never
        assigned sat in the denominator forever.
        """
        reviews = list(self.publication.reviews.all())
        self.assertGreater(len(reviews), 1, "fixture needs >1 reviewer")
        for index, review in enumerate(reviews):
            review.user.technical_working_group = (
                TechnicalWorkingGroup.met if index % 2
                else TechnicalWorkingGroup.dwa
            )
            review.user.save()
            review.is_completed = True
            review.save()
        self.assertLess(2, len(TechnicalWorkingGroup.FieldStr))
        self.assertEqual(progress_reviews(self.publication), "2/2")

    def test_reviewer_without_a_twg_moves_no_counter(self):
        for review in self.publication.reviews.all():
            review.user.technical_working_group = None
            review.user.save()
        self.assertEqual(reviewers_required(self.publication), 0)
        # With no TWG-assigned reviewers no row can be `ready` — the UI must
        # not show a falsely green queue.
        for row in self._rows(page_size=100):
            self.assertNotEqual(row["status"], ValidationStatus.ready)

    # ---- permissions -----------------------------------------------------
    def test_reviewer_is_forbidden(self):
        """The queue exposes every colleague's submitted D-class."""
        self.client.force_authenticate(user=self.reviewer)
        for url in (self.stats_url, self.table_url):
            self.assertEqual(
                self.client.get(url).status_code, status.HTTP_403_FORBIDDEN
            )

    def test_anonymous_is_unauthorized(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get(self.stats_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unknown_publication_is_404(self):
        res = self.client.get(
            reverse(
                "validation-queue-stats",
                kwargs={"version": "v1", "pk": 999999},
            )
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(USE_TZ=False, TEST_ENV=True)
class SubmissionsLeakGuardTestCase(APITestCase):
    """D-1: `submissions` carries every colleague's D-class. It must never
    reach a reviewer, on any of the three /reviewer/* response shapes."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 2)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )
        self.publication = Publication.objects.first()
        self.user = SystemUser.objects.get(
            pk=self.publication.reviews.first().user_id
        )
        self.client.force_authenticate(user=self.user)

    def _url(self, name, **extra):
        return reverse(
            name,
            kwargs={"version": "v1", "pk": self.publication.id, **extra},
        )

    def test_absent_from_the_table(self):
        res = self.client.get(self._url("review-queue-administrations"))
        for row in res.data["data"]:
            self.assertNotIn("submissions", row)

    def test_absent_from_the_map(self):
        res = self.client.get(self._url("review-queue-map"))
        for row in res.data["data"]:
            self.assertNotIn("submissions", row)

    def test_absent_from_the_detail(self):
        administration_id = self.publication.initial_values[0][
            "administration_id"
        ]
        res = self.client.get(
            self._url(
                "review-queue-administration",
                administration_id=administration_id,
            )
        )
        self.assertNotIn("submissions", res.data["administration"])
