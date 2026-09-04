from datetime import date

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import (
    Publication,
    Administration,
    PublicationRaster,
    Review,
)
from api.v1.v1_publication.constants import (
    DroughtCategory,
    RasterIndicatorTypes,
)
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    AdministrationNormal,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)
from api.v1.v1_weather.utils import window_keys


@override_settings(USE_TZ=False, TEST_ENV=True)
class ReviewQueueAPIsTestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 2)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

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

    def _seed_confidence(self, rank=0.5):
        """Everything the 0-5 confidence score needs, agreeing perfectly.

        A satellite SPI rank of 0.5 is a z of 0, and a station total equal to
        the climatology mean is also 0 — delta 0, so every Inkhundla scores
        5 (high). Without this the queue is all zeroes with a `meta.reason`,
        which is correct behaviour but tests nothing about banding.
        """
        administration_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        PublicationRaster.objects.create(
            publication=self.publication,
            indicator=RasterIndicatorTypes.spi,
            geonode_id=1,
            values=[
                {"administration_id": a, "value": rank}
                for a in administration_ids
            ],
        )
        source = WeatherSource.objects.create(
            base_url="https://example.invalid", collection_id="c"
        )
        regions = set(
            Administration.objects.filter(
                pk__in=administration_ids
            ).values_list("region", flat=True)
        )
        year_month = self.publication.year_month
        for index, region in enumerate(r for r in regions if r):
            station = WeatherStation.objects.create(
                source=source,
                wigos_id=f"0-999-0-{index:04d}",
                name=f"{region} station",
                region=region,
                latitude=-26.3,
                longitude=31.1,
            )
            for year, month in window_keys(
                year_month.year, year_month.month
            ):
                for day in range(1, 29):
                    StationDailyAggregate.objects.create(
                        station=station,
                        date=date(year, month, day),
                        parameter=WeatherParameter.precipitation,
                        # 84 days totalling the 100mm climatology mean.
                        value=100 / 84,
                    )
        for administration_id in administration_ids:
            for parameter, value in (
                (WeatherParameter.precip_3m_mean, 100.0),
                (WeatherParameter.precip_3m_sd, 40.0),
            ):
                AdministrationNormal.objects.create(
                    administration_id=administration_id,
                    month=year_month.month,
                    parameter=parameter,
                    value=value,
                    dataset="CHIRPS 1991-2020",
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
        self.assertIsInstance(summary["high_confidence"]["value"], int)
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
        # Two publications on fixed months, replacing the seeded ones. The
        # seeder anchors its months on "now", so deriving `later` from a
        # seeded month with `+31 days` skipped past the next seeded month
        # whenever that month was shorter than 31 days — `_previous_rows` then
        # compared against a publication this test never touched.
        initial_values = self.publication.initial_values
        Publication.objects.all().delete()

        previous = Publication.objects.create(
            year_month=date(2026, 1, 1),
            cdi_geonode_id=987653,
            initial_values=initial_values,
            due_date=date(2026, 1, 15),
        )
        # One Inkhundla reviewed last month -> one fewer "not started" there.
        Review.objects.create(
            publication=previous,
            user=self.user,
            is_completed=True,
            completed_at=timezone.now(),
            suggestion_values=[{
                "administration_id": initial_values[0]["administration_id"],
                "category": DroughtCategory.d2,
                "reviewed": True,
            }],
        )

        # A later publication with no reviews at all -> everything not started.
        # Nothing is seeded beyond `previous`, so any positive offset is safe.
        later = Publication.objects.create(
            year_month=date(2026, 2, 1),
            cdi_geonode_id=987654,
            initial_values=initial_values,
            due_date=date(2026, 2, 15),
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
        # An integer 0-5 always, with 0 meaning "an input was missing" and
        # meta.reason naming which one — never a null or a placeholder.
        self.assertIn(row["confidence"]["value"], range(6))
        self.assertIn("reason", row["confidence"]["meta"])
        self.assertEqual(
            set(row["stations_vs_satellite"]), {"spi", "lst", "lst_reason"}
        )

    def test_table_zone_filter(self):
        zone = Administration.objects.exclude(zone=None).first().zone
        res = self.client.get(
            f"{self.table_url}?zone={zone}&page_size=100"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["data"])
        self.assertTrue(all(r["zone"] == zone for r in res.data["data"]))

    def test_table_confidence_filter(self):
        self._seed_confidence()
        res = self.client.get(
            f"{self.table_url}?confidence=high&page_size=100"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["data"])
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

    def _split_reviews(self):
        """(my review, another reviewer's review or None)."""
        mine = self.publication.reviews.get(user_id=self.user.id)
        theirs = self.publication.reviews.exclude(
            user_id=self.user.id
        ).first()
        return mine, theirs

    def test_table_reviewed_filter_is_scoped_to_me(self):
        """"Review completed" lists the Tinkhundla THIS reviewer submitted.

        Not team completion (N/N): that showed rows the reviewer had never
        touched and hid ones they had.
        """
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        mine_only, theirs_only = adm_ids[0], adm_ids[1]
        my_review, their_review = self._split_reviews()
        self._submit(my_review, mine_only, DroughtCategory.d2)
        if their_review:
            self._submit(their_review, theirs_only, DroughtCategory.d1)

        res = self.client.get(f"{self.table_url}?reviewed=true&page_size=100")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {r["administration_id"] for r in res.data["data"]}
        self.assertIn(mine_only, ids)
        if their_review:
            self.assertNotIn(theirs_only, ids)
        self.assertTrue(
            all(
                r["my_suggestion"]["reviewed"] for r in res.data["data"]
            )
        )

    def test_table_reviewed_filter_matches_reviewed_card(self):
        """The chip and the "Tinkhundla reviewed" card count the same rows."""
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        my_review, _ = self._split_reviews()
        for adm_id in adm_ids[:3]:
            self._submit(my_review, adm_id, DroughtCategory.d2)

        table = self.client.get(
            f"{self.table_url}?reviewed=true&page_size=100"
        )
        stats = self.client.get(self.stats_url)
        self.assertEqual(
            table.data["total"],
            stats.data["summary"]["tinkhundla_reviewed"]["value"],
        )

    def test_table_awaiting_filter_is_the_complement_of_completed(self):
        """"Awaiting review" is every row "Review completed" leaves out.

        `reviewed` is tri-state: absent = all, true = done, false = to do. It
        used to default to False and be coerced with `or None`, which made
        `reviewed=false` a synonym for "All" — the whole table, including rows
        the reviewer had already finished.
        """
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        my_review, their_review = self._split_reviews()
        for adm_id in adm_ids[:3]:
            self._submit(my_review, adm_id, DroughtCategory.d2)
        # another reviewer's work must not count as mine
        if their_review:
            self._submit(their_review, adm_ids[3], DroughtCategory.d1)

        def ids(query):
            res = self.client.get(f"{self.table_url}?{query}page_size=100")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            return {r["administration_id"] for r in res.data["data"]}

        every = ids("")
        done = ids("reviewed=true&")
        awaiting = ids("reviewed=false&")

        self.assertEqual(done, set(adm_ids[:3]))
        self.assertTrue(awaiting)                      # not an empty table
        self.assertEqual(done | awaiting, every)       # together: everything
        self.assertFalse(done & awaiting)              # apart: no overlap
        if their_review:
            # theirs is submitted, but not by me, so it is still mine to do
            self.assertIn(adm_ids[3], awaiting)

    def test_table_page_past_the_end_serves_the_last_page(self):
        """A page that ran off the end is a stale bookmark, not a bad request.

        The reviewer is returned to the page they came from, but "Awaiting
        review" drops a row on every submission — so 6 pages becomes 5 while
        they are inside an Inkhundla. DRF's default 404 ("Invalid page.")
        rejected the fetch and took the whole queue render down with it.
        """
        rows = self.client.get(f"{self.table_url}?page_size=100").data["total"]
        self.assertGreater(rows, 10)          # needs >1 page to be meaningful
        last_page = -(-rows // 10)            # ceil

        res = self.client.get(f"{self.table_url}?page={last_page + 3}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["current"], last_page)
        self.assertTrue(res.data["data"])
        self.assertEqual(res.data["total"], rows)

    def test_table_page_past_the_end_of_an_empty_queue(self):
        """An emptied queue clamps to page 1 and returns no rows, never 404."""
        my_review, _ = self._split_reviews()
        for value in self.publication.initial_values:
            self._submit(
                my_review, value["administration_id"], DroughtCategory.d2
            )
        # nothing is awaiting any more
        res = self.client.get(f"{self.table_url}?reviewed=false&page=6")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["current"], 1)
        self.assertEqual(res.data["data"], [])
        self.assertEqual(res.data["total"], 0)

    def test_map_awaiting_filter_matches_the_table(self):
        """The map takes the same chip, so Prev/Next walks the same rows."""
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        my_review, _ = self._split_reviews()
        self._submit(my_review, adm_ids[0], DroughtCategory.d2)

        table = self.client.get(
            f"{self.table_url}?reviewed=false&page_size=100"
        )
        map_res = self.client.get(f"{self.map_url}?reviewed=false")
        self.assertEqual(
            {r["administration_id"] for r in table.data["data"]},
            {r["administration_id"] for r in map_res.data["data"]},
        )
        self.assertNotIn(
            adm_ids[0],
            {r["administration_id"] for r in map_res.data["data"]},
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
        self._seed_confidence()
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
    def test_map_reviewed_filter_is_scoped_to_me(self):
        adm_ids = [
            v["administration_id"] for v in self.publication.initial_values
        ]
        mine_only, theirs_only = adm_ids[0], adm_ids[1]
        my_review, their_review = self._split_reviews()
        self._submit(my_review, mine_only, DroughtCategory.d2)
        if their_review:
            self._submit(their_review, theirs_only, DroughtCategory.d1)

        res = self.client.get(f"{self.map_url}?reviewed=true")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {r["administration_id"] for r in res.data["data"]}
        self.assertIn(mine_only, ids)
        if their_review:
            self.assertNotIn(theirs_only, ids)
        self.assertTrue(
            all(r["my_suggestion"]["reviewed"] for r in res.data["data"])
        )

    # ---- auth ------------------------------------------------------------
    def test_requires_authentication(self):
        self.client.logout()
        res = self.client.get(self.stats_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
