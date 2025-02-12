from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from api.v1.v1_init.models import Settings


class TSContactViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.secret_key = "test_secret_key"
        self.headers = {"HTTP_X_SECRET_KEY": self.secret_key}
        self.url = reverse(
            "contacts_ts",
            kwargs={"version": "v1"}
        )

    def test_get_contacts_success(self):
        """Test retrieving contacts when settings exist"""
        Settings.objects.create(
            secret_key=self.secret_key,
            ts_emails=["support@example.com", "help@example.com"]
        )

        response = self.client.get(self.url, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            "contacts": ["support@example.com", "help@example.com"]
        })

    def test_get_contacts_invalid_secret_key(self):
        """Test request with an invalid secret key"""
        Settings.objects.create(
            secret_key=self.secret_key,
            ts_emails=["support@example.com"]
        )

        response = self.client.get(
            self.url,
            HTTP_X_SECRET_KEY="invalid_key"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
