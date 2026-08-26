import io
import tempfile
from PIL import Image
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector
from utils import storage


def _png_upload():
    buf = io.BytesIO()
    Image.new("RGB", (200, 100), "blue").save(buf, format="PNG")
    buf.seek(0)
    buf.name = "map.png"
    return buf


@override_settings(USE_TZ=False, TEST_ENV=True)
class SourceFileTestCase(APITestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._settings = override_settings(STORAGE_PATH=self.tmp)
        self._settings.enable()
        storage.STORAGE_PATH = self.tmp
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)

    def tearDown(self):
        self._settings.disable()

    def _url(self):
        return reverse("activity-source-file",
                       kwargs={"version": "v1", "pk": self.activity.pk})

    def test_upload_and_download(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            self._url(), {"source_file": _png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.data["source_file"], "activity/ACT-WASH-1/map.png")
        download = self.client.get(self._url())
        self.assertEqual(download.status_code, status.HTTP_200_OK)

    def test_download_missing_is_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.get(self._url()).status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_type_rejected(self):
        self.client.force_authenticate(self.admin)
        bad = io.BytesIO(b"data")
        bad.name = "x.exe"
        resp = self.client.post(
            self._url(), {"source_file": bad}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_replace_allowed_when_active(self):
        self.client.force_authenticate(self.admin)
        self.activity.status = ActivityStatus.active
        self.activity.save()
        resp = self.client.post(
            self._url(), {"source_file": _png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_replace_blocked_when_archived(self):
        self.client.force_authenticate(self.admin)
        self.activity.status = ActivityStatus.archived
        self.activity.save()
        resp = self.client.post(
            self._url(), {"source_file": _png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_cannot_replace(self):
        reviewer = SystemUser.objects.create(
            email="lead@x.org", name="Lead", role=UserRoleTypes.reviewer,
            activity_sector=ActivitySector.wash)
        self.client.force_authenticate(reviewer)
        resp = self.client.post(
            self._url(), {"source_file": _png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
