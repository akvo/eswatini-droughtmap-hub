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
                "pending_review", "high_confidence", "tinkhundla_reviewed",
                "overall_readiness", "reviews_collected", "status_breakdown",
            },
        )
        self.assertTrue(summary["high_confidence"]["is_mock"])
        breakdown = {b["key"]: b["value"] for b in summary["status_breakdown"]}
        self.assertEqual(sum(breakdown.values()), self.total)

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
            "flat",  # neither month is validated yet
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

    def test_table_reviewed_filter_counts_in_progress_reviews(self):
        # The reviewer marks Tinkhundla one by one and submits the review only
        # once they are all done — an Inkhundla reviewed inside a review that
        # is still open must already count as reviewed.
        review = self.publication.reviews.get(user_id=self.user.id)
        adm_id = self.publication.initial_values[0]["administration_id"]
        review.suggestion_values = [{
            "administration_id": adm_id,
            "category": DroughtCategory.d2,
            "reviewed": True,
        }]
        review.is_completed = False
        review.completed_at = None
        review.save()

        res = self.client.get(f"{self.table_url}?reviewed=true&page_size=100")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        rows = {r["administration_id"]: r for r in res.data["data"]}
        self.assertIn(adm_id, rows)
        self.assertEqual(rows[adm_id]["reviews"]["completed"], 1)
        self.assertNotEqual(rows[adm_id]["review_status"], "not_started")

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

    # ---- map -------------------------------------------------------------
    def test_map_reviewed_filter(self):
        review = self.publication.reviews.first()
        adm_id = self.publication.initial_values[0]["administration_id"]
        review.suggestion_values = [
            {"administration_id": adm_id, "category": DroughtCategory.d2,
             "reviewed": True}
        ]
        review.is_completed = True
        review.completed_at = timezone.now()
        review.save()

        res = self.client.get(f"{self.map_url}?reviewed=true")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            all(r["review_status"] != "not_started" for r in res.data["data"])
        )
        self.assertIn(
            adm_id, [r["administration_id"] for r in res.data["data"]]
        )

    # ---- auth ------------------------------------------------------------
    def test_requires_authentication(self):
        self.client.logout()
        res = self.client.get(self.stats_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
