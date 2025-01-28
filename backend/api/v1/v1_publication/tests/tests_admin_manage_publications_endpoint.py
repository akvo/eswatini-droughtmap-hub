from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
)
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_jobs.models import Jobs


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

    def test_create_publication(self):
        url = reverse("publication-list", kwargs={"version": "v1"})
        data = {
            "cdi_geonode_id": 1,
            "year_month": "2025-01-01",
            "initial_values": [
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
            "due_date": "2025-02-28",
            "reviewers": [r.id for r in self.reviewers],
            "subject": "CDI Map review requested for month 2025-01",
            "message": (
                "Dear {{reviewer_name}},"
                "<br/>The CDI Map for the month of "
                "{{year_month}} is available for review."
                "Please submit your review by {{due_date}}."
            ),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Publication.objects.count(), 1)
        self.assertCountEqual(
            sorted(list(response.json().keys())),
            sorted(
                [
                    "id",
                    "cdi_geonode_id",
                    "year_month",
                    "initial_values",
                    "status",
                    "due_date",
                    "validated_values",
                    "published_at",
                    "narrative",
                    "bulletin_url",
                    "created_at",
                    "updated_at",
                ]
            ),
        )
        data = response.json()
        self.assertEqual(
            data["status"],
            PublicationStatus.in_review,
        )
        self.assertEqual(
            data["initial_values"],
            [
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
        )
        publication = Publication.objects.get(pk=data["id"])
        self.assertEqual(
            publication.reviews.count(),
            2
        )
        # 2 send email jobs to reviewers
        self.assertEqual(
            Jobs.objects.count(),
            2
        )

    def test_publication_list(self):
        call_command("fake_publications_seeder", "--test", True)
        url = reverse("publication-list", kwargs={"version": "v1"})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            data["total"],
            Publication.objects.count(),
        )
        self.assertCountEqual(
            sorted(list(data["data"][0])),
            sorted([
                "id",
                "year_month",
                "due_date",
                "initial_values",
                "status",
            ])
        )

    def test_publication_detail(self):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2025-01-01",
            initial_values=[
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
            due_date="2025-02-28",
        )
        url = reverse(
            "publication-details",
            kwargs={"version": "v1", "pk": publication.id}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["id"],
            publication.id
        )

    def test_update_publication(self):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2025-01-01",
            initial_values=[
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
            due_date="2025-02-28",
        )
        url = reverse(
            "publication-details",
            kwargs={"version": "v1", "pk": publication.id}
        )
        data = {
            "validated_values": [
                {"value": 1, "administration_id": 1253002, "category": "d4"},
                {"value": 14, "administration_id": 1253053, "category": "d3"},
            ],
            "status": PublicationStatus.published,
            "narrative": "<p>This is a narrative</p>",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        publication.refresh_from_db()
        self.assertEqual(publication.narrative, "<p>This is a narrative</p>")
        self.assertEqual(publication.status, PublicationStatus.published)
        self.assertEqual(
            publication.validated_values,
            [
                {"value": 1, "administration_id": 1253002, "category": "d4"},
                {"value": 14, "administration_id": 1253053, "category": "d3"},
            ],
        )

    def test_soft_delete_publication(self):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2025-01-01",
            initial_values=[
                {"value": 3.5, "administration_id": 1253002, "category": "d3"},
                {"value": 32, "administration_id": 1253053, "category": "d0"},
            ],
            due_date="2025-02-28",
        )
        url = reverse(
            "publication-details",
            kwargs={"version": "v1", "pk": publication.id}
        )
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        publication.refresh_from_db()
        self.assertIsNotNone(publication.deleted_at)
        self.assertEqual(Publication.objects.count(), 0)
        self.assertEqual(Publication.objects_deleted.count(), 1)
