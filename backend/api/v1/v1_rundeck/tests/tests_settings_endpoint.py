from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api.v1.v1_rundeck.models import Settings
from api.v1.v1_users.models import SystemUser as User


class SettingsViewSetTests(APITestCase):

    def setUp(self):
        """Set up test users and a sample Settings instance."""
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.regular_user = User.objects._create_user(
            username="user", email="user@example.com", password="userpass"
        )

        self.settings = Settings.objects.create(
            project_name="Test Project",
            job_id="12345",
            on_success_emails=["success@example.com"],
            on_failure_emails=["failure@example.com"],
            on_exceeded_emails=["exceeded@example.com"],
        )

        self.settings_url = reverse(
            "settings",
            kwargs={
                "version": "v1",
            }
        )  # URL for list and create
        self.detail_url = reverse(
            "settings-details",
            kwargs={
                "version": "v1",
                "pk": self.settings.pk
            }
        )  # Detail URL

    def test_admin_can_list_settings(self):
        """Admin users should be able to list settings."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_list_settings(self):
        """Non-admin users should not be able to list settings."""
        self.client.login(username="user", password="userpass")
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_list_settings(self):
        """Anonymous users should not be able to list settings."""
        response = self.client.get(self.settings_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_settings(self):
        """Admin users should be able to create settings."""
        self.client.login(username="admin", password="adminpass")
        data = {
            "project_name": "New Project",
            "job_id": "67890",
            "on_success_emails": ["new_success@example.com"],
            "on_failure_emails": ["new_failure@example.com"],
        }
        response = self.client.post(self.settings_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Settings.objects.count(), 2)

    def test_non_admin_cannot_create_settings(self):
        """Non-admin users should not be able to create settings."""
        self.client.login(username="user", password="userpass")
        data = {
            "project_name": "New Project",
            "job_id": "67890",
            "on_success_emails": ["new_success@example.com"],
            "on_failure_emails": ["new_failure@example.com"],
        }
        response = self.client.post(self.settings_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_settings(self):
        """Admin users should be able to update settings."""
        self.client.login(username="admin", password="adminpass")
        data = {
            "project_name": "Updated Project",
            "job_id": "99999",
            "on_success_emails": ["updated_success@example.com"],
            "on_failure_emails": ["updated_failure@example.com"],
            "on_exceeded_emails": ["updated_exceeded@example.com"],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.project_name, "Updated Project")
        self.assertEqual(
            self.settings.on_success_emails, ["updated_success@example.com"]
        )
        self.assertEqual(
            self.settings.on_failure_emails, ["updated_failure@example.com"]
        )
        self.assertEqual(
            self.settings.on_exceeded_emails, ["updated_exceeded@example.com"]
        )

    def test_non_admin_cannot_update_settings(self):
        """Non-admin users should not be able to update settings."""
        self.client.login(username="user", password="userpass")
        data = {
            "project_name": "Unauthorized Update",
            "job_id": "99999",
            "on_success_emails": ["updated_success@example.com"],
            "on_failure_emails": ["updated_failure@example.com"],
            "on_exceeded_emails": ["updated_exceeded@example.com"],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_settings(self):
        """Admin users should be able to delete settings."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Settings.objects.count(), 0)

    def test_non_admin_cannot_delete_settings(self):
        """Non-admin users should not be able to delete settings."""
        self.client.login(username="user", password="userpass")
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
