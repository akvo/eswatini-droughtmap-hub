from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector


@override_settings(USE_TZ=False, TEST_ENV=True)
class ActivityCrudTestCase(APITestCase):
    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.lead = SystemUser.objects.create(
            email="lead@x.org", name="Lead", role=UserRoleTypes.reviewer,
            activity_sector=ActivitySector.wash)
        self.list_url = reverse("activity-list", kwargs={"version": "v1"})

    def _detail(self, pk):
        return reverse("activity-detail", kwargs={"version": "v1", "pk": pk})

    def test_anonymous_cannot_list(self):
        self.assertIn(
            self.client.get(self.list_url).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_forces_draft_and_generates_code(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(self.list_url, {
            "sector": ActivitySector.wash, "title": "Tanker dispatch",
            "triggers": {"dclass": {"class": 3, "months": 4},
                         "vuln": {"op": 1, "value": 2},
                         "exp": [{"indicator": "population", "op": 1,
                                  "value": 2000}],
                         "other": None},
            "response_type": 2,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["code"], "ACT-WASH-1")
        self.assertEqual(resp.data["status"], ActivityStatus.draft)

    def test_reviewer_cannot_create(self):
        self.client.force_authenticate(self.lead)
        resp = self.client.post(self.list_url, {
            "sector": ActivitySector.wash, "title": "X"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_cannot_edit_own_sector_draft(self):
        self.client.force_authenticate(self.lead)
        activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        resp = self.client.patch(
            self._detail(activity.pk), {"title": "B"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_may_read(self):
        self.client.force_authenticate(self.lead)
        ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        self.assertEqual(
            self.client.get(self.list_url).status_code, status.HTTP_200_OK)

    def test_admin_can_edit_active(self):
        self.client.force_authenticate(self.admin)
        activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash,
            status=ActivityStatus.active)
        resp = self.client.patch(
            self._detail(activity.pk), {"title": "B"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        activity.refresh_from_db()
        self.assertEqual(activity.title, "B")
        self.assertEqual(activity.status, ActivityStatus.active)

    def test_edit_blocked_when_archived(self):
        self.client.force_authenticate(self.admin)
        activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash,
            status=ActivityStatus.archived)
        resp = self.client.patch(
            self._detail(activity.pk), {"title": "B"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reviewer_cannot_delete(self):
        self.client.force_authenticate(self.lead)
        activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        resp = self.client.delete(self._detail(activity.pk))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_soft_deletes(self):
        self.client.force_authenticate(self.admin)
        activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        resp = self.client.delete(self._detail(activity.pk))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ResponseActivity.objects.count(), 0)
        self.assertEqual(ResponseActivity.objects_with_deleted.count(), 1)

    def test_sector_immutable_on_update(self):
        self.client.force_authenticate(self.admin)
        activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        resp = self.client.patch(
            self._detail(activity.pk),
            {"sector": ActivitySector.food}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        activity.refresh_from_db()
        self.assertEqual(activity.sector, ActivitySector.wash)
        self.assertEqual(activity.code, "ACT-WASH-1")
