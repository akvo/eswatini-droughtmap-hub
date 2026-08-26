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


class ReviewersTreeAccessTestCase(APITestCase):
    """Who may read the reviewer roster (BB-3 D-4).

    Widened from `IsAdmin` to `IsAdmin | IsReviewer`. Both halves matter: a
    reviewer needs the roster to forward a brief, and an admin must not lose
    access they had — StartPublicationSlideIn reads the same endpoint.

    The gate is deliberately on ROLE, not TWG membership. Reading the roster
    and being allowed to send are different questions: BriefForwardView still
    refuses a sender with no TWG, so a TWG-less reviewer can see colleagues
    here and still not forward a brief.
    """

    def setUp(self):
        self.url = "/api/v1/admin/reviewers-tree"

    def _user(self, email, role, twg):
        return SystemUser.objects.create(
            email=email, name=email, role=role, technical_working_group=twg
        )

    def test_anonymous_is_rejected(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reviewer_with_twg_may_read_the_roster(self):
        self.client.force_authenticate(
            user=self._user(
                "twg_reviewer@test.com",
                UserRoleTypes.reviewer,
                TechnicalWorkingGroup.ndma,
            )
        )
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_200_OK
        )

    def test_admin_without_a_twg_keeps_access(self):
        self.client.force_authenticate(
            user=self._user("plain_admin@test.com", UserRoleTypes.admin, None)
        )
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_200_OK
        )

    def test_reviewer_without_a_twg_may_still_read_the_roster(self):
        """Reading is not sending: BriefForwardView is where the TWG gate
        lives, and it is unchanged."""
        self.client.force_authenticate(
            user=self._user("no_twg@test.com", UserRoleTypes.reviewer, None)
        )
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_200_OK
        )

    def test_observer_is_rejected(self):
        self.client.force_authenticate(
            user=self._user(
                "observer@test.com", UserRoleTypes.observer, None
            )
        )
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )
