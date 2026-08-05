from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import BriefForwardLog


class BriefForwardAPITestCase(APITestCase):
    def setUp(self):
        self.twg_user = SystemUser.objects.create(
            email="twg_member@example.com",
            name="TWG Member",
            role=2,
            technical_working_group=1,
        )
        self.non_twg_user = SystemUser.objects.create(
            email="non_twg@example.com",
            name="Non TWG Member",
            role=2,
            technical_working_group=None,
        )
        self.url = reverse("brief-forward", kwargs={"version": "v1"})
        self.valid_payload = {
            "inkhundla_id": 4588078,
            "inkhundla_name": "Big Bend",
            "components": ["cover_header", "kpi_tiles"],
            "recipients": [
                {"email": "recipient1@example.com", "name": "Recipient One"}
            ],
            "note": "Please review.",
            "brief_url": "http://localhost:3000/brief-builder?inkhundla=4588078",  # noqa
        }

    def test_unauthenticated_returns_401(self):
        res = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_twg_user_returns_403(self):
        self.client.force_authenticate(user=self.non_twg_user)
        res = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            res.data.get("detail"),
            "TWG membership required to forward briefs.",
        )

    def test_empty_recipients_returns_400(self):
        self.client.force_authenticate(user=self.twg_user)
        invalid_payload = {**self.valid_payload, "recipients": []}
        res = self.client.post(self.url, invalid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recipients", res.data)

    def test_invalid_recipient_email_returns_400(self):
        self.client.force_authenticate(user=self.twg_user)
        invalid_payload = {
            **self.valid_payload,
            "recipients": [{"email": "not-an-email", "name": "Invalid"}],
        }
        res = self.client.post(self.url, invalid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recipients", res.data)

    @patch("api.v1.v1_publication.brief.view.async_task")
    def test_valid_forward_creates_log_and_queues_task(self, mock_async_task):
        self.client.force_authenticate(user=self.twg_user)
        res = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(res.data, {"queued": True, "recipient_count": 1})

        log = BriefForwardLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.sender, self.twg_user)
        self.assertEqual(log.inkhundla_name, "Big Bend")
        mock_async_task.assert_called_once()
