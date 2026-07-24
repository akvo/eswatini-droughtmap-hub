from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_users.constants import TechnicalWorkingGroup


class ReviewersTreeEndpointTestCase(APITestCase):
    def setUp(self):
        # Create an admin user for authentication
        self.admin_user = SystemUser.objects.create_superuser(
            email="admin@test.com",
            password="Password123!",
            name="Admin User",
            role=UserRoleTypes.admin,
            email_verified=True,
        )
        self.client.force_authenticate(user=self.admin_user)

        # Create reviewers
        self.reviewer_ndma = SystemUser.objects._create_user(
            email="ndma_rev@test.com",
            password="Password123!",
            name="NDMA Reviewer",
        )
        self.reviewer_ndma.role = UserRoleTypes.reviewer
        self.reviewer_ndma.email_verified = True
        self.reviewer_ndma.technical_working_group = TechnicalWorkingGroup.ndma
        self.reviewer_ndma.save()

        self.reviewer_unassigned = SystemUser.objects._create_user(
            email="unassigned_rev@test.com",
            password="Password123!",
            name="Unassigned Reviewer",
        )
        self.reviewer_unassigned.role = UserRoleTypes.reviewer
        self.reviewer_unassigned.email_verified = True
        self.reviewer_unassigned.technical_working_group = None
        self.reviewer_unassigned.save()

        self.url = "/api/v1/admin/reviewers-tree"

    def test_get_reviewers_tree_grouped_correctly(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check NDMA group is present
        ndma_group = next((g for g in data if g["value"] == "twg-1"), None)
        self.assertIsNotNone(ndma_group)
        self.assertEqual(
            ndma_group["title"],
            TechnicalWorkingGroup.FieldStr[TechnicalWorkingGroup.ndma],
        )
        self.assertFalse(ndma_group["selectable"])

        # Check reviewer in NDMA group
        reviewer_node = next(
            (
                c
                for c in ndma_group["children"]
                if c["value"] == self.reviewer_ndma.id
            ),
            None,
        )
        self.assertIsNotNone(reviewer_node)
        self.assertEqual(reviewer_node["title"], self.reviewer_ndma.name)
        self.assertEqual(reviewer_node["subtitle"], self.reviewer_ndma.email)
        self.assertTrue(reviewer_node["email_verified"])
        self.assertTrue(reviewer_node["selectable"])

        # Check Unassigned group is present
        unassigned_group = next(
            (g for g in data if g["value"] == "twg-unassigned"), None
        )
        self.assertIsNotNone(unassigned_group)
        self.assertEqual(unassigned_group["title"], "Unassigned")
        self.assertFalse(unassigned_group["selectable"])

        # Check reviewer in Unassigned group
        reviewer_un_node = next(
            (
                c
                for c in unassigned_group["children"]
                if c["value"] == self.reviewer_unassigned.id
            ),
            None,
        )
        self.assertIsNotNone(reviewer_un_node)
        self.assertEqual(
            reviewer_un_node["title"], self.reviewer_unassigned.name
        )
        self.assertTrue(reviewer_un_node["selectable"])

        # Check that empty groups (like MET, MoAg, etc.) are omitted
        moag_group = next((g for g in data if g["value"] == "twg-2"), None)
        self.assertIsNone(moag_group)
