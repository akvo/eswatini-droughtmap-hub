from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status
from api.v1.v1_init.models import Settings
from api.v1.v1_users.models import SystemUser, UserRoleTypes


class AdminContactViewTest(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        self.client = APIClient()
        self.secret_key = "test_secret_key"

        Settings.objects.create(
            secret_key=self.secret_key
        )
        self.headers = {"HTTP_X_SECRET_KEY": self.secret_key}
        self.url = reverse(
            "contacts_admin",
            kwargs={"version": "v1"}
        )

    def test_get_contacts_success(self):
        response = self.client.get(self.url, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        admins = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).all()
        contacts = [
            a.email
            for a in admins
        ]
        self.assertEqual(response.data, {
            "contacts": contacts
        })
