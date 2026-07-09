from unittest.mock import patch
from django.conf import settings
from rest_framework import status
from .base import BaseIKSTestCase


class IKSDownloadTriggerEndpointTests(BaseIKSTestCase):

    @patch("api.v1.v1_iks.views.async_task")
    def test_iks_download_trigger_with_api_key(self, mock_async_task):
        """
        Test POST /api/v1/iks/download/monthly with valid
        and invalid X-API-Key headers.
        """
        url = "/api/v1/iks/download/monthly"
        self.client.force_authenticate(
            user=None
        )  # De-authenticate to test API Key only

        # Test invalid/missing header
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test valid header
        settings.X_API_KEY = "test-secret"
        response = self.client.post(url, HTTP_X_API_KEY="test-secret")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mock_async_task.call_count, 1)
