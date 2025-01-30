from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import (
    Review,
    Publication,
    PublicationStatus,
)
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=True)
class PublicationViewSetTestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 3)
        self.user = (
            SystemUser.objects.filter(
                role=UserRoleTypes.admin
            ).order_by("?").first()
        )
        self.client.force_authenticate(user=self.user)

        self.reviewers = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).order_by("?")[:2]

    def test_get_pending_publication_reviews(self):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2025-01-01",
            initial_values=[
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
            due_date="2025-02-28",
        )
        publication.reviews.set([
            Review(publication=publication, user=reviewer)
            for reviewer in self.reviewers
        ], bulk=False)
        url = reverse(
            "publication-reviews",
            kwargs={"version": "v1", "pk": publication.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"id": f"{publication.id}", "reviews": []},
        )

    def test_get_completed_publication_reviews(self):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2025-01-01",
            initial_values=[
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
            due_date="2025-02-28",
        )
        publication.reviews.set([
            Review(publication=publication, user=reviewer)
            for reviewer in self.reviewers
        ], bulk=False)
        for reviewer in publication.reviews.all():
            reviewer.is_completed = True
            reviewer.completed_at = "2025-01-01T00:00:00Z"
            reviewer.save()
        publication.status = PublicationStatus.in_validation
        publication.save()
        url = reverse(
            "publication-reviews",
            kwargs={"version": "v1", "pk": publication.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            data["id"],
            f"{publication.id}",
        )
        self.assertEqual(
            len(data["reviews"]),
            2,
        )

    def test_get_publication_reviews_not_found(self):
        url = reverse(
            "publication-reviews",
            kwargs={"version": "v1", "pk": 999999},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(),
            {"detail": "No Publication matches the given query."},
        )
