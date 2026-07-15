from rest_framework import status
from .base import BaseIKSTestCase


class IKSAdministrationEndpointTests(BaseIKSTestCase):

    def test_iks_administration_list_endpoint_anonymous(self):
        """Test GET /api/v1/iks/administrations anonymously."""
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/iks/administrations")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return list including our seeded administration
        data = response.json()
        self.assertTrue(len(data) >= 1)
        admin_item = [a for a in data if a["id"] == self.admin_area.id][0]
        self.assertEqual(admin_item["name"], self.admin_area.name)
        self.assertEqual(admin_item["region"], self.admin_area.region)
        self.assertEqual(admin_item["zone"], self.admin_area.zone)
