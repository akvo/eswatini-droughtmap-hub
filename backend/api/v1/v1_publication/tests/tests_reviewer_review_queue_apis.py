from datetime import timedelta

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import Publication, Administration
from api.v1.v1_publication.constants import DroughtCategory


@override_settings(USE_TZ=False, TEST_ENV=True)
class ReviewQueueAPIsTestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 2)
        call_command("fake_publications_seeder", "--test", True)

        self.publication = Publication.objects.first()
        self.total = len(self.publication.initial_values)
        self.user = SystemUser.objects.get(
            pk=self.publication.reviews.first().user_id
        )
        self.client.force_authenticate(user=self.user)

        def url(name, **extra):
            return reverse(
                name, kwargs={"version": "v1", "pk": self.publication.id,
                              **extra}
            )
        self.stats_url = url("review-queue-stats")
        self.table_url = url("review-queue-administrations")
        self.map_url = url("review-queue-map")
        self.detail_url = lambda adm: url(
            "review-queue-administration", administration_id=adm
        )

    # ---- stats -----------------------------------------------------------
    def test_stats_shape(self):
        res = self.client.get(self.stats_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(set(res.data), {"meta", "summary"})
        summary = res.data["summary"]
        self.assertEqual(
            set(summary),
            {
                "pending_review", "disagreements", "high_confidence",
                "tinkhundla_reviewed", "overall_readiness",
                "reviews_collected", "status_breakdown",
            },
        )
        self.assertTrue(summary["high_confidence"]["is_mock"])
        breakdown = {b["key"]: b["value"] for b in summary["status_breakdown"]}
        self.assertEqual(sum(breakdown.values()), self.total)

    def _mark_reviewed(self, review, administration_ids):
        review.suggestion_values = [
            {"administration_id": a, "category": DroughtCategory.d1,
             "reviewed": True}
            for a in administration_ids
        ]
        review.save()

    def test_tinkhundla_reviewed_is_my_own_not_the_validator_output(self):
        """The card is the requesting reviewer's progress.

        It used to read Publication.validated_values — the NDRMA validator's
        output, which is empty for the whole review stage, so the card sat at
        0 exactly when reviewers were using it.
        """
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        self._mark_reviewed(
            self.publication.reviews.get(user_id=self.user.id), adm_ids[:3]
        )
        # Validator output on every Inkhundla must not feed this card.
        self.publication.validated_values = [
            {"administration_id": a, "category": DroughtCategory.d2}
            for a in adm_ids
        ]
        self.publication.save()

        card = self.client.get(self.stats_url).data["summary"][
            "tinkhundla_reviewed"
        ]
        self.assertEqual(card["value"], 3)
        self.assertEqual(card["total"], self.total)

    def test_pending_review_and_reviewed_are_halves_of_the_total(self):
        """`pending_review` is outstanding review work, not the disagreement
        count it used to carry under that title."""
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        self._mark_reviewed(
            self.publication.reviews.get(user_id=self.user.id), adm_ids[:5]
        )
        summary = self.client.get(self.stats_url).data["summary"]
        self.assertEqual(summary["tinkhundla_reviewed"]["value"], 5)
        self.assertEqual(summary["pending_review"]["value"], self.total - 5)
        self.assertEqual(
            summary["pending_review"]["value"]
            + summary["tinkhundla_reviewed"]["value"],
            self.total,
        )
        # the disagreement signal keeps its own key
        self.assertIn("disagreements", summary)

    def test_reviews_collected_is_my_own_progress(self):
        """Reviews collected + overall readiness are the requesting reviewer's
        own progress out of the 59 Tinkhundla (Figma 25/59), never crossed with
        other reviewers — a colleague finishing everything changes nothing.
        """
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        self._mark_reviewed(
            self.publication.reviews.get(user_id=self.user.id), adm_ids[:25]
        )
        other = self.publication.reviews.exclude(user_id=self.user.id).first()
        if other:  # a reviewer who has done everything
            self._mark_reviewed(other, adm_ids)

        summary = self.client.get(self.stats_url).data["summary"]
        self.assertEqual(summary["reviews_collected"]["value"], 25)
        self.assertEqual(summary["reviews_collected"]["total"], self.total)
        self.assertEqual(
            summary["overall_readiness"], round(25 / self.total * 100)
        )

    def test_stats_delta_is_null_without_previous_publication(self):
        earliest = Publication.objects.order_by("year_month").first()
        res = self.client.get(
            reverse(
                "review-queue-stats",
                kwargs={"version": "v1", "pk": earliest.id},
            )
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        summary = res.data["summary"]
        self.assertIsNone(summary["pending_review"]["delta"])
        self.assertIsNone(summary["tinkhundla_reviewed"]["delta"])
        self.assertTrue(
            all(b["delta"] is None for b in summary["status_breakdown"])
        )

    def test_stats_delta_against_previous_publication(self):
        earliest = Publication.objects.order_by("year_month").first()
        # One Inkhundla reviewed last month -> one fewer "not started" there.
        review = earliest.reviews.first()
        review.suggestion_values = [{
            "administration_id": (
                earliest.initial_values[0]["administration_id"]
            ),
            "category": DroughtCategory.d2,
            "reviewed": True,
        }]
        review.is_completed = True
        review.completed_at = timezone.now()
        review.save()

        # A later publication with no reviews at all -> everything not started.
        later = Publication.objects.create(
            year_month=earliest.year_month + timedelta(days=31),
            cdi_geonode_id=987654,
            initial_values=earliest.initial_values,
            due_date=earliest.due_date + timedelta(days=31),
        )
        res = self.client.get(
            reverse(
                "review-queue-stats",
                kwargs={"version": "v1", "pk": later.id},
            )
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        breakdown = {
            b["key"]: b for b in res.data["summary"]["status_breakdown"]
        }
        # last month one Inkhundla had left "not started"; this month none has
        self.assertEqual(
            breakdown["not_started"]["delta"], {"value": 1, "direction": "up"}
        )
        self.assertEqual(
            res.data["summary"]["tinkhundla_reviewed"]["delta"]["direction"],
            # The card tracks THIS reviewer's own sign-offs (it used to track
            # the validator's output): the new publication carries none yet,
            # so their progress is down against last month.
            "down",
        )

    # ---- administrations table ------------------------------------------
    def test_table_paginated_shape(self):
        res = self.client.get(self.table_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(set(res.data), {"current", "total", "total_page",
                                         "data"})
        self.assertEqual(res.data["total"], self.total)
        self.assertLessEqual(len(res.data["data"]), 10)  # default page size
        row = res.data["data"][0]
        self.assertEqual(
            set(row),
            {
                "administration_id", "name", "region", "zone", "cdi_class",
                "stations_vs_satellite", "confidence", "reviews",
                "my_suggestion", "assigned_score", "review_status", "disputed",
            },
        )
        self.assertTrue(row["confidence"]["is_mock"])
        self.assertTrue(row["stations_vs_satellite"]["is_mock"])

    def test_table_zone_filter(self):
        zone = Administration.objects.exclude(zone=None).first().zone
        res = self.client.get(
            f"{self.table_url}?zone={zone}&page_size=100"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["data"])
        self.assertTrue(all(r["zone"] == zone for r in res.data["data"]))

    def test_table_confidence_filter(self):
        res = self.client.get(
            f"{self.table_url}?confidence=high&page_size=100"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            all(r["confidence"]["band"] == "high" for r in res.data["data"])
        )

    def _submit(self, review, administration_id, category, reviewed=True):
        vals = list(review.suggestion_values or [])
        vals = [
            v for v in vals if v["administration_id"] != administration_id
        ]
        vals.append({
            "administration_id": administration_id,
            "category": category,
            "reviewed": reviewed,
        })
        review.suggestion_values = vals
        review.save()

    def test_table_reviewed_filter_is_fully_reviewed(self):
        """"Review completed" lists Tinkhundla EVERY assigned reviewer has
        submitted (progress N/N) — not ones only some reviewers touched, which
        made the chip identical to "All".
        """
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        full, partial = adm_ids[0], adm_ids[1]
        reviewers = list(self.publication.reviews.all())
        for review in reviewers:  # everyone submits `full`
            self._submit(review, full, DroughtCategory.d2)
        # only the first reviewer submits `partial`
        self._submit(reviewers[0], partial, DroughtCategory.d1)

        res = self.client.get(f"{self.table_url}?reviewed=true&page_size=100")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {r["administration_id"] for r in res.data["data"]}
        self.assertIn(full, ids)
        if len(reviewers) > 1:
            self.assertNotIn(partial, ids)  # N/N only; partial is excluded
        self.assertTrue(
            all(
                r["review_status"] == "fully_reviewed"
                for r in res.data["data"]
            )
        )

    def test_table_carries_my_own_suggestion(self):
        # D-Class shows the reviewer's own class; assigned_score is the
        # validated one and stays empty until a validator signs the month off.
        review = self.publication.reviews.get(user_id=self.user.id)
        adm_id = self.publication.initial_values[0]["administration_id"]
        review.suggestion_values = [{
            "administration_id": adm_id,
            "category": DroughtCategory.d1,
            "reviewed": True,
            "comment": "Drier than the satellite suggests",
        }]
        review.save()

        res = self.client.get(f"{self.table_url}?page_size=100")
        rows = {r["administration_id"]: r for r in res.data["data"]}
        self.assertEqual(
            rows[adm_id]["my_suggestion"],
            {
                "category": DroughtCategory.d1,
                "reviewed": True,
                "comment": "Drier than the satellite suggests",
            },
        )
        self.assertIsNone(rows[adm_id]["assigned_score"])
        # an Inkhundla this reviewer has not touched carries no suggestion
        other = self.publication.initial_values[1]["administration_id"]
        self.assertIsNone(rows[other]["my_suggestion"])

    def test_stats_high_confidence_drops_once_accepted(self):
        # "ready to bulk-accept" must reach zero after the reviewer accepts
        # them, so the bulk-accept banner disappears.
        res = self.client.get(self.stats_url)
        before = res.data["summary"]["high_confidence"]["value"]
        self.assertGreater(before, 0)

        table = self.client.get(
            f"{self.table_url}?confidence=high&page_size=100"
        )
        review = self.publication.reviews.get(user_id=self.user.id)
        review.suggestion_values = [
            {
                "administration_id": row["administration_id"],
                "category": row["cdi_class"],
                "reviewed": True,
            }
            for row in table.data["data"]
        ]
        review.save()

        res = self.client.get(self.stats_url)
        self.assertEqual(res.data["summary"]["high_confidence"]["value"], 0)

    def test_table_invalid_filter_rejected(self):
        res = self.client.get(f"{self.table_url}?confidence=bogus")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- administration detail ------------------------------------------
    def test_detail_returns_row_and_my_review(self):
        adm_id = self.publication.initial_values[0]["administration_id"]
        res = self.client.get(self.detail_url(adm_id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["administration"]["administration_id"], adm_id
        )
        self.assertEqual(
            res.data["my_review"]["review_id"],
            self.publication.reviews.get(user_id=self.user.id).id,
        )

    def test_detail_unknown_administration_404(self):
        res = self.client.get(self.detail_url(1))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_cdi_block(self):
        adm_id = self.publication.initial_values[0]["administration_id"]
        res = self.client.get(self.detail_url(adm_id))
        cdi = res.data["administration"]["cdi"]
        self.assertEqual(
            set(cdi), {"score", "category", "indicators", "history"}
        )
        self.assertEqual(
            cdi["category"], res.data["administration"]["cdi_class"]
        )
        self.assertIsInstance(cdi["indicators"], list)
        # history plots oldest -> newest: current month is the last point.
        self.assertEqual(
            cdi["history"][-1]["period"],
            self.publication.year_month.strftime("%Y-%m"),
        )

    def test_detail_decision_history_is_own_reviewer_only(self):
        adm_id = self.publication.initial_values[0]["administration_id"]
        mine = self.publication.reviews.get(user_id=self.user.id)
        mine.suggestion_values = [
            {"administration_id": adm_id, "category": DroughtCategory.d2,
             "reviewed": True, "comment": "mine"}
        ]
        mine.save()
        other = self.publication.reviews.exclude(
            user_id=self.user.id
        ).first()
        if other:
            other.suggestion_values = [
                {"administration_id": adm_id, "category": DroughtCategory.d4,
                 "reviewed": True, "comment": "theirs"}
            ]
            other.save()
        res = self.client.get(self.detail_url(adm_id))
        history = res.data["administration"]["decision_history"]
        cats = [h["category"] for h in history]
        self.assertIn(DroughtCategory.d2, cats)          # my own pick
        self.assertNotIn(DroughtCategory.d4, cats)       # other reviewer's

    # ---- map -------------------------------------------------------------
    def test_map_reviewed_filter_is_fully_reviewed(self):
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        full, partial = adm_ids[0], adm_ids[1]
        reviewers = list(self.publication.reviews.all())
        for review in reviewers:
            self._submit(review, full, DroughtCategory.d2)
        self._submit(reviewers[0], partial, DroughtCategory.d1)

        res = self.client.get(f"{self.map_url}?reviewed=true")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {r["administration_id"] for r in res.data["data"]}
        self.assertIn(full, ids)
        if len(reviewers) > 1:
            self.assertNotIn(partial, ids)
        self.assertTrue(
            all(
                r["review_status"] == "fully_reviewed"
                for r in res.data["data"]
            )
        )

    # ---- auth ------------------------------------------------------------
    def test_requires_authentication(self):
        self.client.logout()
        res = self.client.get(self.stats_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
