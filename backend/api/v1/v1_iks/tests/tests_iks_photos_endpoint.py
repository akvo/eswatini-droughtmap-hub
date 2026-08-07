import os
from tempfile import TemporaryDirectory
from django.test import override_settings
from rest_framework import status
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from .base import BaseIKSTestCase


class IKSPhotosEndpointTests(BaseIKSTestCase):

    def test_iks_photos_endpoint_anonymous(self):
        """Test GET /api/v1/iks/{administration_id}/photos anonymously."""
        self.client.force_authenticate(user=None)

        # 1. Test empty case
        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/photos")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["photos"], [])

        # 2. Test with attachments and metadata seeded
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="photo_indicator"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=self.admin_area.created_at,
            submitted_by="CS-200",
            instance_name="June 2026 Report",
            geo=[-26.8203, 31.3117],
            raw_data={
                "inkhundla": "Nkwene",
                "soil_moisture": "Dry",
                "vegetation": "Green",
                "_attachments": [
                    {
                        "filename": "test_photo.jpg",
                        "download_url": "https://kobo.example/test_photo.jpg",
                    }
                ],
            },
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/photos")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        photos = response.json()["photos"]
        self.assertEqual(len(photos), 1)
        self.assertEqual(
            photos[0]["url"], "/api/v1/iks/photos/media/test_photo.jpg"
        )
        self.assertEqual(photos[0]["title"], "June 2026 Report")
        self.assertEqual(photos[0]["submitted_with"], "June 2026 Report")
        self.assertEqual(photos[0]["validated_by"], "TWG")
        self.assertEqual(photos[0]["inkhundla"], "Nkwene")
        self.assertEqual(photos[0]["citizen_scientist"], "CS-200")
        self.assertEqual(photos[0]["soil_moisture"], "Dry")
        self.assertEqual(photos[0]["vegetation"], "Green")
        self.assertEqual(photos[0]["gps"], "-26.82030°N, 31.31170°E")

    def test_iks_photo_file_serve(self):
        """
        Test serving local files downloaded from Kobo via IKSPhotoFileView.
        """
        self.client.force_authenticate(user=None)

        with TemporaryDirectory() as tmp_dir:
            # Create a mock file in temporary folder
            file_name = "test_photo_on_disk.jpg"
            file_path = os.path.join(tmp_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(b"mock_image_data")

            # Override STORAGE_PATH setting so Django serves from tmp_dir
            with override_settings(STORAGE_PATH=tmp_dir):
                response = self.client.get(
                    f"/api/v1/iks/photos/media/{file_name}"
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.headers["Content-Type"], "image/jpeg"
                )
                self.assertEqual(
                    b"".join(response.streaming_content), b"mock_image_data"
                )

    def test_iks_photo_file_serve_not_found(self):
        """Test serving non-existent photo returns 404."""
        self.client.force_authenticate(user=None)
        response = self.client.get(
            "/api/v1/iks/photos/media/missing_photo.jpg"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
