"""Every date the API emits is ISO.

The frontend parses `due_date` with dayjs and an explicit "YYYY-MM-DD" mask.
DRF's DATE_FORMAT used to be "%d-%m-%Y", so serializers that did not opt out
sent "30-12-2024" and dayjs rendered "Invalid Date" — the review queue header
and the individual review deadline pill both shipped that way.

This asserts the setting, not one serializer: the failure mode is a global
default that a new serializer inherits silently.
"""
from datetime import date

from django.test import TestCase
from rest_framework.settings import api_settings

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.serializers import (
    PublicationInfoSerializer,
    PublicationSerializer,
)


class APIDateFormatTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publication = Publication.objects.create(
            year_month=date(2024, 11, 1),
            cdi_geonode_id=987654,
            initial_values=[{"administration_id": 1, "value": 0.5}],
            due_date=date(2024, 12, 30),
            status=PublicationStatus.in_review,
        )

    def test_default_date_format_is_iso(self):
        self.assertEqual(api_settings.DATE_FORMAT, "%Y-%m-%d")

    def test_due_date_is_iso_on_every_serializer_that_exposes_it(self):
        for serializer_class in (
            PublicationInfoSerializer,
            PublicationSerializer,
        ):
            with self.subTest(serializer=serializer_class.__name__):
                data = serializer_class(instance=self.publication).data
                self.assertEqual(data["due_date"], "2024-12-30")

    def test_year_month_keeps_its_own_narrower_format(self):
        data = PublicationInfoSerializer(instance=self.publication).data
        self.assertEqual(data["year_month"], "2024-11")
