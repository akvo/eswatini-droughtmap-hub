from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class OpenAPIContractSchemaTestCase(APITestCase):
    def test_schema_contains_risk_level_tag(self):
        url = reverse("schema")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if Swagger schema is produced and contains the tags definition
        schema_content = response.content.decode("utf-8")
        self.assertIn("Risk Level - Indicators", schema_content)
        self.assertIn("Risk Level - Scoring", schema_content)
