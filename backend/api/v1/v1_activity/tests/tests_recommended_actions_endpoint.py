from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory


@override_settings(USE_TZ=False, TEST_ENV=True)
class RecommendedActionsTestCase(APITestCase):
    def setUp(self):
        # Seed the four ACT-* activities as ACTIVE.
        call_command("generate_activity_seeder", "--test", True)
        self.viewer = SystemUser.objects.create(
            email="v@x.org", name="Viewer", role=UserRoleTypes.reviewer)
        # Administrations whose names exist in priority_areas.csv.
        self.nkwene = Administration.objects.create(
            id=101, name="Nkwene", region="Shiselweni")
        self.sigwe = Administration.objects.create(
            id=102, name="Sigwe", region="Shiselweni")
        self.kumethula = Administration.objects.create(
            id=103, name="Kumethula", region="Shiselweni")
        self.hosea = Administration.objects.create(
            id=104, name="Hosea", region="Lubombo")
        # Categories are set here, deliberately, per case.
        Publication.objects.create(
            year_month="2025-02-01", cdi_geonode_id=1, due_date="2025-03-01",
            initial_values=[],
            validated_values=[
                {"administration_id": 101, "category": DroughtCategory.d3},
                {"administration_id": 102, "category": DroughtCategory.d2},
                {"administration_id": 103, "category": DroughtCategory.d4},
                {"administration_id": 104, "category": DroughtCategory.d0}],
            status=PublicationStatus.published, published_at=timezone.now())

    def _url(self, adm_id=None):
        base = reverse("recommended-actions", kwargs={"version": "v1"})
        return base if adm_id is None else f"{base}?administration_id={adm_id}"

    def _codes(self, resp):
        return sorted(item["code"] for item in resp.data["recommended"])

    # --- Regression cases (authenticated: public + institutional) --------

    def test_nkwene_d3(self):
        # D3: WASH-1 (pop 8956>=2000), HEALTH-1 (pop>=1000), COORD-1 (D3).
        # FOOD-1 fails: cattle 1364 < 1500.
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(101))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._codes(resp), ["ACT-COORD-1", "ACT-HEALTH-1", "ACT-WASH-1"])

    def test_sigwe_d2(self):
        # D2: WASH-1 and HEALTH-1 (both D2 gates, pop ok). FOOD-1/COORD-1
        # need D3.
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(102))
        self.assertEqual(self._codes(resp), ["ACT-HEALTH-1", "ACT-WASH-1"])

    def test_kumethula_d4_all_fire(self):
        # D4: FOOD-1 fires (cattle 2242>=1500, cropland 3046>=3000);
        # all four fire.
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(103))
        self.assertEqual(
            self._codes(resp),
            ["ACT-COORD-1", "ACT-FOOD-1", "ACT-HEALTH-1", "ACT-WASH-1"])

    def test_hosea_d0_none_fire(self):
        # D0 is below every activity's dclass gate -> empty.
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(104))
        self.assertEqual(resp.data["recommended"], [])

    # --- response_type gating by auth (D-5) ------------------------------

    def test_anonymous_sees_public_only(self):
        # Same as Nkwene D3 but anonymous: only the public HEALTH-1.
        resp = self.client.get(self._url(101))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self._codes(resp), ["ACT-HEALTH-1"])

    # --- matched_on shape ------------------------------------------------

    def test_matched_on_reports_unavailable_dimensions(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(101))
        wash = next(
            i for i in resp.data["recommended"] if i["code"] == "ACT-WASH-1")
        matched = wash["matched_on"]
        self.assertTrue(matched["dclass"]["pass"])
        self.assertEqual(matched["dclass"]["actual_category"],
                         DroughtCategory.d3)
        self.assertEqual(matched["vuln"]["source"], "unavailable")
        exp = matched["exp"][0]
        self.assertEqual(exp["indicator"], "population")
        self.assertEqual(exp["actual"], 8956)
        self.assertTrue(exp["pass"])

    # --- errors / empties ------------------------------------------------

    def test_missing_param_400(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_integer_param_400(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(f"{self._url()}?administration_id=abc")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_admin_404(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(999999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_published_map_empty(self):
        Publication.objects.all().delete()
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(self._url(101))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["recommended"], [])
        self.assertIsNone(resp.data["drought_category"])
