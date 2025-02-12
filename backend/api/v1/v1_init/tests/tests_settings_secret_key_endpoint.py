from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from api.v1.v1_init.models import Settings
from api.v1.v1_users.models import SystemUser


class SecretKeyAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = SystemUser.objects.create_superuser(
            name="admin", email="admin@example.com", password="admin123"
        )
        self.client.force_authenticate(user=self.admin_user)
        self.url = reverse(
            "secret_key",
            kwargs={"version": "v1"}
        )

    def test_generate_secret_key(self):
        """Test generating a new secret key"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("secret_key", response.data)

        # Ensure the secret key is stored in the database
        self.assertTrue(
            Settings.objects.filter(
                secret_key=response.data["secret_key"]
            ).exists()
        )

    def test_update_secret_key(self):
        """Test updating the secret key"""
        settings = Settings.objects.create(secret_key="old_secret_key")

        response = self.client.put(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("secret_key", response.data)

        # Ensure the new key is different
        self.assertNotEqual(
            settings.secret_key,
            response.data["secret_key"]
        )

        # Ensure the old key is replaced
        updated_settings = Settings.objects.latest("created_at")
        self.assertEqual(
            updated_settings.secret_key,
            response.data["secret_key"]
        )

    def test_generate_secret_key_unauthorized(self):
        """Test unauthorized access to secret key generation"""
        self.client.force_authenticate(user=None)  # Logout the admin
        response = self.client.post(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_update_secret_key_unauthorized(self):
        """Test unauthorized access to secret key update"""
        self.client.force_authenticate(user=None)  # Logout the admin
        response = self.client.put(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )
