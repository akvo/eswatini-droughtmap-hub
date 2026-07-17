from rest_framework import status
from .base import BaseIKSTestCase


class IKSSoilTrendAggregationEndpointTests(BaseIKSTestCase):

    def test_iks_soil_trend_endpoint_anonymous(self):
        """Test GET /api/v1/iks/aggregations/soil-trend anonymously."""
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("weeks", response.json())
        self.assertIn("soil_trend", response.json())
        self.assertIn("veg_trend", response.json())
        self.assertIn("region_map", response.json())
        # Check fallback value structure
        self.assertEqual(len(response.json()["soil_trend"]["dry"]), 13)
        self.assertEqual(len(response.json()["veg_trend"]["green"]), 13)

    def test_iks_soil_trend_endpoint_with_data(self):
        """Test GET /api/v1/iks/aggregations/soil-trend with values in DB.

        Soil moisture indicator is stored with name='soil_moisture' by the
        download command (see download_iks_data.py).  The value is a raw Kobo
        choice slug such as '1__dry__womile' — the view matches it via
        substring checks, NOT exact match.
        """
        from django.utils import timezone
        from datetime import datetime
        from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue

        soil_indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="soil_moisture"
        )
        veg_indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="vegetation_greenness"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=999,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
        )
        # Use raw Kobo slug values (as stored by download_iks_data)
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=soil_indicator,
            value="1__dry__womile",
        )
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=veg_indicator,
            value="1__generally_green_almost_green_everywhe",
        )

        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Day 10 of May → week index 1 (10 // 7 = 1)
        self.assertEqual(response.json()["soil_trend"]["dry"][1], 100.0)
        self.assertEqual(response.json()["soil_trend"]["moist"][1], 0.0)
        self.assertEqual(response.json()["soil_trend"]["wet"][1], 0.0)

        # Should populate green percentage at index 1
        self.assertEqual(response.json()["veg_trend"]["green"][1], 100.0)
        self.assertEqual(response.json()["veg_trend"]["some"][1], 0.0)
        self.assertEqual(response.json()["veg_trend"]["brown"][1], 0.0)

    def _veg_bucket_for(self, slug, kobo_id):
        """Post one vegetation answer and return its veg_trend split."""
        from django.utils import timezone
        from datetime import datetime
        from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue

        veg_indicator, _ = IKSIndicator.objects.get_or_create(
            kobo_form=self.form, name="vegetation_greenness"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=kobo_id,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
        )
        IKSValue.objects.create(
            kobo_id=kobo_id,
            administration=self.admin_area,
            iks_indicator=veg_indicator,
            value=slug,
        )
        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Day 10 of May → week index 1
        return {
            k: response.json()["veg_trend"][k][1]
            for k in ("green", "some", "brown")
        }

    def test_real_kobo_some_green_slug_is_not_counted_as_green(self):
        """The live 'some' slug ends in '_green', so the bare 'green' branch
        would swallow it. Slug copied verbatim from a real submission."""
        split = self._veg_bucket_for(
            "2__some_few_are_green__timbalwa_letiluhl", 1001
        )
        self.assertEqual(split["some"], 100.0)
        self.assertEqual(split["green"], 0.0)

    def test_shortened_some_green_slug_still_counted_as_some(self):
        """A reworded/shortened choice label must still land in 'some'."""
        split = self._veg_bucket_for("2__some_green_tiluhlata", 1002)
        self.assertEqual(split["some"], 100.0)
        self.assertEqual(split["green"], 0.0)

    def test_real_kobo_brown_slug(self):
        split = self._veg_bucket_for("3__brown__bushile", 1003)
        self.assertEqual(split["brown"], 100.0)
        self.assertEqual(split["green"], 0.0)

    def test_real_kobo_soil_slugs(self):
        """Choice numbering is not in dry/moist/wet order — match the term."""
        from django.utils import timezone
        from datetime import datetime
        from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue

        soil_indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="soil_moisture"
        )
        # Slugs copied verbatim from live submissions.
        for kobo_id, slug in [
            (2001, "1__dry__womile"),
            (2002, "3__moist__ubutsile"),
            (2003, "2__wet__umanti"),
        ]:
            KoboData.objects.create(
                form=self.form,
                kobo_id=kobo_id,
                submission_time=timezone.make_aware(
                    datetime(2026, 5, 10, 12, 0, 0)
                ),
            )
            IKSValue.objects.create(
                kobo_id=kobo_id,
                administration=self.admin_area,
                iks_indicator=soil_indicator,
                value=slug,
            )

        soil = self.client.get(
            "/api/v1/iks/aggregations/soil-trend"
        ).json()["soil_trend"]
        # One answer each → an even three-way split, no bucket swallowed.
        self.assertEqual(soil["dry"][1], 33.3)
        self.assertEqual(soil["moist"][1], 33.3)
        self.assertEqual(soil["wet"][1], 33.3)
