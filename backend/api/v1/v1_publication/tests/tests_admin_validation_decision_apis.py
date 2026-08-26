from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import (
    ConsensusBand,
    DroughtCategory,
    ValidationStatus,
)
from api.v1.v1_publication.models import Publication, ValidationDecision
from api.v1.v1_publication.validation.decision import (
    build_agreement,
    consensus_band,
    majority_of,
    sync_validated_values,
)
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser


class MajorityAndBandTestCase(APITestCase):
    """D-9 tie-breaking and D-2 banding — the two rules most easily got
    wrong, tested away from any fixture."""

    def test_single_mode(self):
        self.assertEqual(majority_of([3, 3, 2]), (3, False))

    def test_tie_breaks_toward_severity(self):
        """Under-calling drought has asymmetric cost; the validator can
        always pick down."""
        self.assertEqual(majority_of([3, 3, 2, 2]), (3, True))
        self.assertEqual(majority_of([1, 5]), (5, True))

    def test_no_submissions(self):
        self.assertEqual(majority_of([]), (None, False))

    def test_bands(self):
        self.assertEqual(consensus_band(100), ConsensusBand.high)
        self.assertEqual(consensus_band(80), ConsensusBand.high)
        self.assertEqual(consensus_band(79), ConsensusBand.moderate)
        self.assertEqual(consensus_band(60), ConsensusBand.moderate)
        self.assertEqual(consensus_band(59), ConsensusBand.low)
        # 40, not 30: the AC's boundary came from modal-share intuition and
        # is not a meaningful point on this scale.
        self.assertEqual(consensus_band(40), ConsensusBand.low)
        self.assertEqual(consensus_band(39), ConsensusBand.none)
        self.assertEqual(consensus_band(None), ConsensusBand.none)

    def test_a_tie_is_flagged_not_visible_in_the_score(self):
        """[3,3,2,2] scores 80 — genuinely tight agreement about severity —
        so the flag is the only signal that the chip was a coin-flip."""
        agreement = build_agreement([3, 3, 2, 2])
        self.assertEqual(agreement["band"], ConsensusBand.high)
        self.assertTrue(agreement["is_tie"])
        self.assertEqual(agreement["tied_categories"], [2, 3])

    def test_agreement_shape(self):
        agreement = build_agreement([1, 3, 3, 3])
        self.assertEqual(agreement["majority_count"], 3)
        self.assertEqual(agreement["total_submitted"], 4)
        self.assertFalse(agreement["is_tie"])
        self.assertEqual(
            agreement["distribution"],
            [{"category": 1, "count": 1}, {"category": 3, "count": 3}],
        )

    def test_empty_agreement(self):
        agreement = build_agreement([])
        self.assertEqual(agreement["total_submitted"], 0)
        self.assertEqual(agreement["majority_count"], 0)
        self.assertEqual(agreement["band"], ConsensusBand.none)


@override_settings(USE_TZ=False, TEST_ENV=True)
class SyncValidatedValuesTestCase(APITestCase):
    """D-1: the published projection is upserted against initial_values."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )
        self.publication = Publication.objects.first()

    def test_writes_into_a_null_array(self):
        """validated_values is null on a fresh publication. Mapping over it
        would yield nothing and the write would silently no-op."""
        self.publication.validated_values = None
        self.publication.save()
        target = self.publication.initial_values[0]["administration_id"]

        sync_validated_values(self.publication, target, DroughtCategory.d2)

        self.publication.refresh_from_db()
        self.assertEqual(
            len(self.publication.validated_values),
            len(self.publication.initial_values),
        )
        entry = next(
            v
            for v in self.publication.validated_values
            if v["administration_id"] == target
        )
        self.assertEqual(entry["category"], DroughtCategory.d2)

    def test_leaves_other_entries_untouched(self):
        first, second = (
            self.publication.initial_values[0]["administration_id"],
            self.publication.initial_values[1]["administration_id"],
        )
        sync_validated_values(self.publication, first, DroughtCategory.d1)
        sync_validated_values(self.publication, second, DroughtCategory.d3)

        self.publication.refresh_from_db()
        values = {
            v["administration_id"]: v["category"]
            for v in self.publication.validated_values
        }
        self.assertEqual(values[first], DroughtCategory.d1)
        self.assertEqual(values[second], DroughtCategory.d3)


@override_settings(USE_TZ=False, TEST_ENV=True)
class ValidationDecisionAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

        self.publication = Publication.objects.first()
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.reviewer = SystemUser.objects.get(
            pk=self.publication.reviews.order_by("id").first().user_id
        )
        self.administration_id = self.publication.initial_values[0][
            "administration_id"
        ]
        self.client.force_authenticate(user=self.admin)

    def _url(self, name="validation-decision", administration_id=None):
        return reverse(
            name,
            kwargs={
                "version": "v1",
                "pk": self.publication.id,
                "administration_id": (
                    administration_id or self.administration_id
                ),
            },
        )

    def _submit_categories(self, categories, administration_id=None):
        """Give the first N reviewers a submitted D-class."""
        target = administration_id or self.administration_id
        for review, category in zip(
            self.publication.reviews.order_by("id"), categories
        ):
            review.suggestion_values = [
                {
                    "administration_id": target,
                    "category": category,
                    "reviewed": True,
                }
            ]
            review.save()

    # ---- GET -------------------------------------------------------------
    def test_payload_shape(self):
        res = self.client.get(self._url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for key in (
            "meta",
            "administration_id",
            "label",
            "region",
            "zone",
            "status",
            "reviews_completed",
            "reviews_total",
            "consensus",
            "majority_category",
            "validated_category",
            "confidence",
            "confidence_band",
            "is_override",
            "masked",
            "agreement",
            "reviews",
            "decision",
        ):
            self.assertIn(key, res.data, msg=key)
        for key in (
            "publication_id",
            "year_month",
            "reviewers_required",
            "can_submit",
            "viewer",
            "prev_administration_id",
            "next_administration_id",
            "queue_page",
        ):
            self.assertIn(key, res.data["meta"], msg=key)

    def test_one_row_per_assigned_reviewer_submitted_or_not(self):
        """AC-4.1/4.2: pending reviewers still get a row."""
        self._submit_categories([DroughtCategory.d2])
        res = self.client.get(self._url())
        self.assertEqual(
            len(res.data["reviews"]), self.publication.reviews.count()
        )
        pending = [r for r in res.data["reviews"] if r["category"] is None]
        self.assertTrue(pending)
        self.assertIsNone(pending[0]["submitted_at"])

    def test_decision_is_null_before_anything_is_saved(self):
        self.assertIsNone(self.client.get(self._url()).data["decision"])

    def test_unknown_administration_is_404(self):
        res = self.client.get(self._url(administration_id=999999))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ---- masking (D-4) ---------------------------------------------------
    def test_reviewer_who_has_not_submitted_sees_no_colleague_judgements(
        self,
    ):
        self._submit_categories(
            [DroughtCategory.d2, DroughtCategory.d3, DroughtCategory.d1]
        )
        # An assigned reviewer who has not submitted for THIS Inkhundla —
        # the case masking exists for. `_submit_categories` gave the first
        # three a D-class; take one that it did not reach.
        pending = self.publication.reviews.order_by("id")[3]
        pending.suggestion_values = []
        pending.save()
        self.client.force_authenticate(user=pending.user)

        res = self.client.get(self._url())
        self.assertTrue(res.data["masked"])
        self.assertIsNone(res.data["agreement"])
        self.assertIsNone(res.data["consensus"])
        self.assertIsNone(res.data["majority_category"])
        self.assertFalse(res.data["meta"]["can_submit"])
        # The roster count survives; the judgements do not.
        self.assertEqual(
            len(res.data["reviews"]), self.publication.reviews.count()
        )
        # The requester's own row stays intact — they may see what they
        # themselves submitted. Everyone else's judgement and identity go.
        rows = res.data["reviews"]
        own = [r for r in rows if r["user_id"] == pending.user_id]
        others = [r for r in rows if r["user_id"] != pending.user_id]
        self.assertEqual(len(own), 1)
        self.assertFalse(own[0]["hidden"])
        self.assertTrue(others)
        for review in others:
            self.assertTrue(review["hidden"])
            self.assertIsNone(review["category"])
            self.assertIsNone(review["name"])
            self.assertIsNone(review["email"])
            self.assertIsNone(review["comment"])
            # organisation survives: which institutions were asked is not a
            # judgement, and the queue already exposes it.
            self.assertIsNotNone(review["organisation"])

    def test_reviewer_who_has_submitted_sees_everything(self):
        self._submit_categories([DroughtCategory.d2, DroughtCategory.d3])
        self.client.force_authenticate(user=self.reviewer)
        res = self.client.get(self._url())
        self.assertFalse(res.data["masked"])
        self.assertIsNotNone(res.data["agreement"])
        self.assertFalse(res.data["meta"]["can_submit"])

    def test_admin_is_never_masked(self):
        res = self.client.get(self._url())
        self.assertFalse(res.data["masked"])
        self.assertTrue(res.data["meta"]["can_submit"])

    # ---- neighbours (D-7) ------------------------------------------------
    def test_prev_next_walk_the_alphabetical_queue(self):
        res = self.client.get(self._url())
        meta = res.data["meta"]
        queue = self.client.get(
            reverse(
                "validation-queue-administrations",
                kwargs={"version": "v1", "pk": self.publication.id},
            ),
            {"page_size": 100},
        ).data["data"]
        ids = [r["administration_id"] for r in queue]
        index = ids.index(self.administration_id)
        self.assertEqual(
            meta["prev_administration_id"],
            ids[index - 1] if index > 0 else None,
        )
        self.assertEqual(
            meta["next_administration_id"],
            ids[index + 1] if index < len(ids) - 1 else None,
        )

    def test_neighbours_reproduce_the_queue_order_exactly(self):
        """The shared ordered_rows is the point: if the two computed the list
        separately, Next would walk an order the table never shows."""
        queue = self.client.get(
            reverse(
                "validation-queue-administrations",
                kwargs={"version": "v1", "pk": self.publication.id},
            ),
            {"page_size": 100},
        ).data["data"]
        ids = [r["administration_id"] for r in queue]

        walked = [ids[0]]
        guard = 0
        while guard < len(ids) + 5:
            guard += 1
            res = self.client.get(self._url(administration_id=walked[-1]))
            nxt = res.data["meta"]["next_administration_id"]
            if nxt is None:
                break
            walked.append(nxt)
        self.assertEqual(walked, ids)

    def test_queue_page_honours_page_size(self):
        at_ten = self.client.get(self._url(), {"page_size": 10}).data["meta"][
            "queue_page"
        ]
        at_hundred = self.client.get(self._url(), {"page_size": 100}).data[
            "meta"
        ]["queue_page"]
        self.assertGreaterEqual(at_ten, at_hundred)
        self.assertEqual(at_hundred, 1)

    def test_neighbours_survive_the_row_leaving_its_own_filter(self):
        """Validate on the Ready tab and the row becomes `validated`, so
        ?status=ready stops matching it. Prev/Next must not dead-end."""
        self.publication.validated_values = [
            {
                "administration_id": self.administration_id,
                "category": DroughtCategory.d2,
            }
        ]
        self.publication.save()

        res = self.client.get(self._url(), {"status": ValidationStatus.ready})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res.data["meta"]["queue_page"])

    # ---- PUT: draft (AC-6.5) --------------------------------------------
    def test_draft_persists_and_reopens(self):
        res = self.client.put(
            self._url(),
            {
                "category": DroughtCategory.d1,
                "reasoning": "Waiting on the Met station re-check.",
                "is_draft": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        payload = self.client.get(self._url()).data
        self.assertEqual(payload["decision"]["category"], DroughtCategory.d1)
        self.assertEqual(
            payload["decision"]["reasoning"],
            "Waiting on the Met station re-check.",
        )
        self.assertTrue(payload["decision"]["is_draft"])
        # ... and the queue has not moved: a draft is not a publication.
        self.assertIsNone(payload["validated_category"])
        self.assertNotEqual(payload["status"], ValidationStatus.validated)
        self.publication.refresh_from_db()
        self.assertIsNone(self.publication.validated_values)

    def test_draft_may_be_incomplete(self):
        res = self.client.put(self._url(), {"is_draft": True}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # ---- PUT: submit (AC-6.4, 6.6) --------------------------------------
    def test_submit_accepting_the_majority_needs_no_reasoning(self):
        self._submit_categories([DroughtCategory.d2, DroughtCategory.d2])
        res = self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_override"])
        self.assertEqual(res.data["majority_category"], DroughtCategory.d2)
        self.assertIsNotNone(res.data["validated_at"])

        self.publication.refresh_from_db()
        entry = next(
            v
            for v in self.publication.validated_values
            if v["administration_id"] == self.administration_id
        )
        self.assertEqual(entry["category"], DroughtCategory.d2)

    def test_override_without_reasoning_is_rejected(self):
        self._submit_categories([DroughtCategory.d2, DroughtCategory.d2])
        res = self.client.put(
            self._url(),
            {"category": DroughtCategory.d4, "is_draft": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reasoning", res.data)

    def test_override_with_reasoning_records_the_override(self):
        self._submit_categories([DroughtCategory.d2, DroughtCategory.d2])
        res = self.client.put(
            self._url(),
            {
                "category": DroughtCategory.d4,
                "reasoning": "Station data contradicts the composite.",
                "is_draft": False,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_override"])
        self.assertEqual(res.data["majority_category"], DroughtCategory.d2)

    def test_a_tie_requires_reasoning_even_when_accepting_the_chip(self):
        """There is no majority to accept, so the pick is the validator's own
        judgement — and `is_override` is still False (D-9)."""
        self._submit_categories(
            [
                DroughtCategory.d2,
                DroughtCategory.d2,
                DroughtCategory.d1,
                DroughtCategory.d1,
            ]
        )
        blocked = self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tied", str(blocked.data["reasoning"]).lower())

        allowed = self.client.put(
            self._url(),
            {
                "category": DroughtCategory.d2,
                "reasoning": "Two classes tied; taking the more severe.",
                "is_draft": False,
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertFalse(allowed.data["is_override"])

    def test_no_data_cannot_be_submitted(self):
        res = self.client.put(
            self._url(),
            {"category": DroughtCategory.none, "is_draft": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", res.data)

    def test_submitting_without_a_category_is_rejected(self):
        res = self.client.put(self._url(), {"is_draft": False}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", res.data)

    # ---- PUT: snapshot + re-submit (D-6, D-9) ---------------------------
    def test_majority_is_snapshotted_not_recomputed(self):
        """A late review must not rewrite a historical decision from
        accepted to overridden."""
        self._submit_categories([DroughtCategory.d2, DroughtCategory.d2])
        self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        # three more reviewers now say D4, shifting the live majority
        for review in list(self.publication.reviews.all())[2:5]:
            review.suggestion_values = [
                {
                    "administration_id": self.administration_id,
                    "category": DroughtCategory.d4,
                    "reviewed": True,
                }
            ]
            review.save()

        decision = ValidationDecision.objects.get(
            publication=self.publication,
            administration_id=self.administration_id,
        )
        self.assertEqual(decision.majority_category, DroughtCategory.d2)
        self.assertFalse(decision.is_override)
        # the live tally has moved, and says so
        payload = self.client.get(self._url()).data
        self.assertEqual(payload["majority_category"], DroughtCategory.d4)

    def test_resubmitting_re_snapshots(self):
        self._submit_categories([DroughtCategory.d2, DroughtCategory.d2])
        self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        res = self.client.put(
            self._url(),
            {
                "category": DroughtCategory.d4,
                "reasoning": "Corrected after the station re-check.",
                "is_draft": False,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_override"])
        self.assertEqual(
            ValidationDecision.objects.filter(
                publication=self.publication,
                administration_id=self.administration_id,
            ).count(),
            1,
        )

    def test_a_submitted_decision_cannot_return_to_draft(self):
        self._submit_categories([DroughtCategory.d2])
        self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        res = self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_draft", res.data)

    def test_submitting_moves_the_queue_validated_count_by_one(self):
        stats_url = reverse(
            "validation-queue-stats",
            kwargs={"version": "v1", "pk": self.publication.id},
        )
        before = {
            c["key"]: c["value"]
            for c in self.client.get(stats_url).data["data"]
        }
        self._submit_categories([DroughtCategory.d2])
        self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        after = {
            c["key"]: c["value"]
            for c in self.client.get(stats_url).data["data"]
        }
        self.assertEqual(after["validated"], before["validated"] + 1)

    def test_two_submits_on_different_tinkhundla_both_survive(self):
        """The race the queue doc could not close: single-entry upserts touch
        different rows, so neither reverts the other."""
        first, second = (
            self.publication.initial_values[0]["administration_id"],
            self.publication.initial_values[1]["administration_id"],
        )
        for administration_id, category in (
            (first, DroughtCategory.d1),
            (second, DroughtCategory.d3),
        ):
            res = self.client.put(
                self._url(administration_id=administration_id),
                {
                    "category": category,
                    # No reviewer has submitted for these Tinkhundla, so there
                    # is no majority to accept and reasoning is required.
                    "reasoning": "No reviews in; assigning from the raster.",
                    "is_draft": False,
                },
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.publication.refresh_from_db()
        values = {
            v["administration_id"]: v["category"]
            for v in self.publication.validated_values
        }
        self.assertEqual(values[first], DroughtCategory.d1)
        self.assertEqual(values[second], DroughtCategory.d3)

    # ---- permissions -----------------------------------------------------
    def test_reviewer_cannot_submit(self):
        self.client.force_authenticate(user=self.reviewer)
        res = self.client.put(
            self._url(),
            {"category": DroughtCategory.d2, "is_draft": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_may_read(self):
        self.client.force_authenticate(user=self.reviewer)
        self.assertEqual(
            self.client.get(self._url()).status_code, status.HTTP_200_OK
        )

    def test_anonymous_is_unauthorized(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get(self._url()).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


@override_settings(USE_TZ=False, TEST_ENV=True)
class ValidationHistoryAPITestCase(APITestCase):
    """AC-7.1: submitted decisions from EARLIER cycles only."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

        publications = list(Publication.objects.order_by("year_month"))
        if len(publications) < 2:
            self.skipTest("fixture needs two publications")
        self.earlier, self.current = publications[0], publications[-1]
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.administration_id = self.current.initial_values[0][
            "administration_id"
        ]
        self.client.force_authenticate(user=self.admin)

    def _history(self, publication):
        return self.client.get(
            reverse(
                "validation-decision-history",
                kwargs={
                    "version": "v1",
                    "pk": publication.id,
                    "administration_id": self.administration_id,
                },
            )
        )

    def test_empty_before_any_decision_is_recorded(self):
        res = self._history(self.current)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"], [])

    def test_earlier_submitted_decisions_only(self):
        ValidationDecision.objects.create(
            publication=self.earlier,
            administration_id=self.administration_id,
            category=DroughtCategory.d2,
            reasoning="Accepted the reviewer majority.",
            is_draft=False,
            majority_category=DroughtCategory.d2,
            validated_by=self.admin,
        )
        # a draft in the same earlier cycle must not appear
        ValidationDecision.objects.create(
            publication=self.current,
            administration_id=self.administration_id,
            category=DroughtCategory.d3,
            is_draft=True,
        )

        rows = self._history(self.current).data["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], DroughtCategory.d2)
        self.assertFalse(rows[0]["is_override"])
        self.assertEqual(rows[0]["name"], self.admin.name)
        self.assertIsNotNone(rows[0]["initials"])

    def test_the_current_cycle_is_excluded(self):
        ValidationDecision.objects.create(
            publication=self.current,
            administration_id=self.administration_id,
            category=DroughtCategory.d2,
            is_draft=False,
            validated_by=self.admin,
        )
        self.assertEqual(self._history(self.current).data["data"], [])
