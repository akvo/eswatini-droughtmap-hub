from django.test import override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import Publication, Administration
from api.v1.v1_publication.constants import (
    PublicationStatus,
    SECTOR_CONTEXT_MAX_CHARS,
)
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import (
    ActivitySector,
    ActivityStatus,
    ActivityResponseType,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class PublishSectorContextTestCase(APITestCase):
    """The National Overview copy must exist before the map goes out (D-6)."""

    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.client.force_authenticate(self.admin)

        adm = Administration.objects.create(
            id=1, name="Inkhundla A", region="Hhohho")
        values = [{"administration_id": adm.id, "category": 2, "value": 0.4}]

        # Trigger evaluation reads the LATEST PUBLISHED map, so without one
        # nothing fires and no sector would be required. This is the prior
        # month, which is what an admin publishing a new one actually has.
        Publication.objects.create(
            cdi_geonode_id=9000,
            year_month="2026-04-01",
            due_date="2026-05-01",
            initial_values=values,
            validated_values=values,
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

        self.publication = Publication.objects.create(
            cdi_geonode_id=9001,
            year_month="2026-05-01",
            due_date="2026-06-01",
            initial_values=values,
            validated_values=values,
            status=PublicationStatus.in_review,
            narrative="Conditions eased across most of the country.",
        )
        # One active public activity -> exactly one sector is required.
        ResponseActivity.objects.create(
            code="ACT-WASH-1",
            title="Borehole rehabilitation",
            sector=ActivitySector.wash,
            status=ActivityStatus.active,
            response_type=ActivityResponseType.public,
            triggers={"dclass": {"class": 0}},
        )
        self.url = reverse(
            "publication-details",
            kwargs={"version": "v1", "pk": self.publication.pk},
        )

    def _publish(self, **extra):
        return self.client.put(
            self.url,
            {"status": PublicationStatus.published, **extra},
            format="json",
        )

    def test_publish_blocked_without_sector_context(self):
        resp = self._publish()
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector_context", resp.json())
        self.assertIn(
            "Water & Sanitation", resp.json()["sector_context"][0])

    def test_publish_blocked_when_an_entry_is_only_whitespace(self):
        resp = self._publish(
            sector_context={str(ActivitySector.wash): "   "})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector_context", resp.json())

    def test_publish_blocked_without_narrative(self):
        self.publication.narrative = ""
        self.publication.save()
        resp = self._publish(
            sector_context={str(ActivitySector.wash): "Boreholes restored."})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("narrative", resp.json())

    def test_publish_succeeds_and_persists(self):
        resp = self._publish(
            sector_context={str(ActivitySector.wash): "Boreholes restored."})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, PublicationStatus.published)
        self.assertEqual(
            self.publication.sector_context,
            {str(ActivitySector.wash): "Boreholes restored."},
        )

    def test_only_sectors_with_active_public_activities_are_required(self):
        """A sector with nothing active renders no card, so it is not asked
        for — the modal, the overview and this check share one list."""
        resp = self._publish(
            sector_context={str(ActivitySector.wash): "Boreholes restored."})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unknown_sector_id_is_rejected(self):
        resp = self._publish(sector_context={"99": "Not a sector."})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector_context", resp.json())

    def test_non_dict_is_rejected(self):
        resp = self._publish(sector_context=["not", "a", "dict"])
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector_context", resp.json())

    def test_over_length_entry_is_rejected(self):
        resp = self._publish(
            sector_context={
                str(ActivitySector.wash): "x" * (SECTOR_CONTEXT_MAX_CHARS + 1)
            })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sector_context", resp.json())

    def test_untriggered_sector_is_not_required(self):
        """A sector whose activities fire nowhere still renders a card, but
        its paragraph is not demanded — there is no response to describe."""
        ResponseActivity.objects.create(
            code="ACT-TRANS-1",
            title="Relief routes",
            sector=ActivitySector.trans,
            status=ActivityStatus.active,
            response_type=ActivityResponseType.public,
            # Class 5 never fires against the published category of 2.
            triggers={"dclass": {"class": 5}},
        )
        resp = self._publish(
            sector_context={str(ActivitySector.wash): "Boreholes restored."})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_a_triggered_second_sector_is_required(self):
        """The counterpart: once it fires, it must be described."""
        ResponseActivity.objects.create(
            code="ACT-TRANS-2",
            title="Relief routes",
            sector=ActivitySector.trans,
            status=ActivityStatus.active,
            response_type=ActivityResponseType.public,
            triggers={"dclass": {"class": 0}},
        )
        resp = self._publish(
            sector_context={str(ActivitySector.wash): "Boreholes restored."})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Transport & Logistics", resp.json()["sector_context"][0])

    def test_saving_without_publishing_needs_nothing(self):
        """Validated only on the transition to published (D-6)."""
        resp = self.client.put(
            self.url,
            {"status": PublicationStatus.in_validation},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
