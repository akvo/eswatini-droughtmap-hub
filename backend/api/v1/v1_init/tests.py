from django.test import TestCase
from django.core.management import call_command
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_users.tests.mixins import ProfileTestHelperMixin


# Create your tests here.
class HealthCheckTestCase(TestCase, ProfileTestHelperMixin):
    def setUp(self):
        call_command(
            "generate_admin_seeder", "--test", True
        )
        call_command(
            "fake_users_seeder", "--test", True, "--repeat", 1
        )
        admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        reviewer = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).first()
        self.admin_token = self.get_auth_token(
            email=admin.email,
            password="Changeme123"
        )
        self.reviewer_token = self.get_auth_token(
            email=reviewer.email,
            password="Changeme123"
        )

    def test_dummy_success_admin_only_endpoint(self):
        res = self.client.get(
            "/api/v1/dummy/admin-only",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data, {"message": "Admin OK"})

    def test_dummy_reviwer_access_admin_only_endpoint(self):
        res = self.client.get(
            "/api/v1/dummy/admin-only",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.reviewer_token}"
        )
        self.assertEqual(res.status_code, 403)

    def test_dummy_success_reviewer_endpoint(self):
        res = self.client.get(
            "/api/v1/dummy/reviewer-only",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.reviewer_token}"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data, {"message": "Reviewer OK"})

    def test_dummy_admin_access_reviewer_endpoint(self):
        res = self.client.get(
            "/api/v1/dummy/reviewer-only",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}"
        )
        self.assertEqual(res.status_code, 403)
