from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from api.v1.v1_users.models import SystemUser


class SecretKeyAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = SystemUser.objects.create_superuser(
            name="admin", email="admin@example.com", password="admin123"
        )
        self.client.force_authenticate(user=self.admin_user)
        self.url = reverse(
            "settings",
            kwargs={"version": "v1"}
        )

    def test_empty_settings(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"ts_emails": None})

    def test_update_empty_settings(self):
        response = self.client.put(
            self.url,
            {
                "ts_emails": ["help@example.com"]
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_existing_settings(self):
        # Create a new one first
        self.client.post(reverse(
            "secret_key",
            kwargs={"version": "v1"}
        ))

        # update the existing one
        response = self.client.put(
            self.url,
            {
                "ts_emails": ["help@example.com"]
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(response.data),
            [
                "ts_emails",
                "secret_key",
                "created_at",
                "updated_at",
            ]
        )
