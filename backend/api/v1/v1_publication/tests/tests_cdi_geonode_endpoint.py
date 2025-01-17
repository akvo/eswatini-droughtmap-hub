from rest_framework.test import APITestCase
from rest_framework import status
from django.core.management import call_command
from unittest.mock import patch
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import DroughtCategory


class CDIGeonodeAPITestCase(APITestCase):
    def setUp(self):
        self.url = "/api/v1/admin/cdi-geonode"
        call_command(
            "generate_admin_seeder", "--test", True
        )

        self.user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).order_by("?").first()
        self.client.force_authenticate(user=self.user)

        # Mock response data from the external API
        resources = [
            {
                "pk": 1,
                "title": "Test GeoNode Resource",
                "detail_url": "https://geonode.com/catalogue/#/dataset/1",
                "embed_url": "https://geonode.com/datasets/geonode:test/embed",
                "thumbnail_url": (
                    "https://geonode.com/uploaded/thumbs/dataset-3d6e57f3.jpg"
                ),
                "download_url": (
                    "https://geonode.com/datasets/geonode:test"
                    "/dataset_download"
                ),
                "created": "2025-01-15T12:00:00Z",
                "publication": None,
            },
            {
                "pk": 2,
                "title": "Another Resource",
                "detail_url": "http://geonode.com/catalogue/#/dataset/2",
                "embed_url": "http://geonode.com/datasets/geonode:test/embed",
                "thumbnail_url": (
                    "https://geonode.com/uploaded/thumbs/dataset-3d6e89i1.jpg"
                ),
                "download_url": (
                    "https://geonode.com/datasets/geonode:another"
                    "/dataset_download"
                ),
                "created": "2025-01-16T14:00:00Z",
                "publication": None,
            },
        ]
        self.mock_response_data = {
            "total": 2,
            "page": 1,
            "page_size": 10,
            "resources": resources
        }

    @patch("requests.get")  # Mock the requests.get call
    def test_get_cdi_geonode_success(self, mock_get):
        # Configure the mock to return a response with JSON data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["data"][0]["pk"], 1)
        self.assertEqual(
            response.data["data"][0]["title"],
            "Test GeoNode Resource"
        )
        self.assertEqual(
            response.data["data"][0]["detail_url"],
            "https://geonode.com/catalogue/#/dataset/1"
        )
        self.assertEqual(
            response.data["data"][0]["created"],
            "2025-01-15T12:00:00Z"
        )

    @patch("requests.get")
    def test_get_cdi_geonode_error(self, mock_get):
        # Configure the mock to return an error response
        mock_get.return_value.status_code = 500

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.data,
            {"message": "Server Error: Unable to fetch data."}
        )

    @patch("requests.get")
    def test_get_by_unauthenticated_user(self, _):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @patch("requests.get")
    def test_publication_exists(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.mock_response_data
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month="2024-12-01",
            due_date="2025-01-31",
            initial_values=[{
                "administration_id": 1,
                "value": 6,
                "category": DroughtCategory.d3
            }]
        )

        # Perform the GET request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"][0]["publication"],
            publication.pk
        )
