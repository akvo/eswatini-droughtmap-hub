from datetime import datetime

from django.utils import timezone
from rest_framework import status

from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from api.v1.v1_iks.utils import label_soil_moisture, label_vegetation
from api.v1.v1_iks.constants import CHIEFDOM_FIELD
from .base import BaseIKSTestCase


class LabelMappingTests(BaseIKSTestCase):
    """The Section-D slug -> label mapping (G5): match on the siSwati/English
    term, never the numeric prefix (which is not in severity order)."""

    def test_soil_moisture_labels(self):
        self.assertEqual(label_soil_moisture("1__dry__womile"), "Dry")
        self.assertEqual(label_soil_moisture("3__moist__ubutsile"), "Moist")
        self.assertEqual(label_soil_moisture("2__wet__umanti"), "Wet")
        self.assertIsNone(label_soil_moisture(""))
        self.assertIsNone(label_soil_moisture(None))

    def test_vegetation_labels(self):
        self.assertEqual(
            label_vegetation("1__generally_green_almost_green_everywhe"),
            "Generally green",
        )
        self.assertEqual(
            label_vegetation("2__some_few_are_green__timbalwa_letiluhl"),
            "Some/few green",
        )
        self.assertEqual(label_vegetation("3__brown__bushile"), "Brown")


class IKSReviewSummaryEndpointTests(BaseIKSTestCase):
    def _url(self, adm_id, period=None):
        base = f"/api/v1/iks/{adm_id}/review-summary"
        return f"{base}?period={period}" if period else base

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(self._url(self.admin_area.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_state_when_no_reports(self):
        res = self.client.get(self._url(self.admin_area.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["reports_count"], 0)
        self.assertIsNone(res.data["soil_moisture"])
        self.assertIsNone(res.data["vegetation_greenness"])
        self.assertIsNone(res.data["chiefdom"])
        self.assertIsNone(res.data["photo_url"])
        self.assertEqual(res.data["indicators_present"], [])
        self.assertEqual(res.data["locations"], [])

    def _seed(self, kobo_id, when, soil=None, veg=None, indicator=None,
              chiefdom=None, geo=None):
        KoboData.objects.create(
            form=self.form,
            kobo_id=kobo_id,
            submission_time=timezone.make_aware(when),
            geo=geo,
            raw_data={CHIEFDOM_FIELD: chiefdom} if chiefdom else {},
        )
        if soil:
            si, _ = IKSIndicator.objects.get_or_create(
                kobo_form=self.form, name="soil_moisture"
            )
            IKSValue.objects.create(
                kobo_id=kobo_id, administration=self.admin_area,
                iks_indicator=si, value=soil,
            )
        if veg:
            vi, _ = IKSIndicator.objects.get_or_create(
                kobo_form=self.form, name="vegetation_greenness"
            )
            IKSValue.objects.create(
                kobo_id=kobo_id, administration=self.admin_area,
                iks_indicator=vi, value=veg,
            )
        if indicator:
            ii, _ = IKSIndicator.objects.get_or_create(
                kobo_form=self.form, name=indicator
            )
            IKSValue.objects.create(
                kobo_id=kobo_id, administration=self.admin_area,
                iks_indicator=ii, value="observed",
            )

    def test_cards_chiefdom_location_and_indicators(self):
        self._seed(
            101, datetime(2026, 5, 10, 12, 0),
            soil="1__dry__womile",
            veg="3__brown__bushile",
            indicator="9__f___frogs_calling_singing__emacoco_ak",
            chiefdom="Engcongwane chiefdom",
            geo={"latitude": -26.5, "longitude": 31.3},
        )
        res = self.client.get(self._url(self.admin_area.id, "2026-05"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["reports_count"], 1)
        self.assertEqual(res.data["soil_moisture"]["value_label"], "Dry")
        self.assertEqual(res.data["vegetation_greenness"]["value_label"],
                         "Brown")
        self.assertEqual(res.data["chiefdom"], "Engcongwane chiefdom")
        self.assertEqual(res.data["locations"],
                         [{"lat": -26.5, "lon": 31.3}])
        # section-D indicators are excluded from the reported-indicator slugs
        self.assertIn("9__f___frogs_calling_singing__emacoco_ak",
                      res.data["indicators_present"])
        self.assertNotIn("soil_moisture", res.data["indicators_present"])

    def test_cards_use_most_recent_submission(self):
        # OQ-6: two reports same month, newest wins.
        self._seed(201, datetime(2026, 5, 5, 9, 0), soil="2__wet__umanti")
        self._seed(202, datetime(2026, 5, 20, 9, 0), soil="1__dry__womile")
        res = self.client.get(self._url(self.admin_area.id, "2026-05"))
        self.assertEqual(res.data["reports_count"], 2)
        self.assertEqual(res.data["soil_moisture"]["value_label"], "Dry")

    def test_period_filter_excludes_other_months(self):
        self._seed(301, datetime(2026, 4, 10, 9, 0), soil="2__wet__umanti")
        res = self.client.get(self._url(self.admin_area.id, "2026-05"))
        self.assertEqual(res.data["reports_count"], 0)
        self.assertIsNone(res.data["soil_moisture"])
