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

        # 2. Test with attachments seeded
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="photo_indicator"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=self.admin_area.created_at,
            raw_data={
                "_attachments": [
                    {
                        "filename": "test_photo.jpg",
                        "download_url": "https://kobo.example/test_photo.jpg",
                    }
                ]
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
            photos[0]["url"], "https://kobo.example/test_photo.jpg"
        )
