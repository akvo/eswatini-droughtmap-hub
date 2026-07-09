from rest_framework import status
from api.v1.v1_iks.models import IKSIndicator
from .base import BaseIKSTestCase


class IKSIndicatorsEndpointTests(BaseIKSTestCase):

    def test_iks_indicators_list_endpoint(self):
        """Test GET /api/v1/iks/indicators API."""
        IKSIndicator.objects.create(
            kobo_form=self.form, name="Indicator Frogs"
        )
        response = self.client.get("/api/v1/iks/indicators")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], "Indicator Frogs")
