"""Shared test fixtures for the CDI Explorer (INS-3)."""
from datetime import date

from django.utils import timezone

from api.v1.v1_publication.constants import (
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationRaster,
)

MHLANGATANE = 4588078  # Hhohho / highveld — has published data
KWALUSENI = 2042786  # Manzini — never appears in any published month

# Ascending. 2026-02 is deliberately absent from the calendar run so the
# padding is exercised, and 2026-03 is published but carries no decision or
# raster value for Mhlangatane.
PUBLISHED_MONTHS = ["2025-12", "2026-01", "2026-03", "2026-04", "2026-05"]
COVERED_MONTHS = ["2025-12", "2026-01", "2026-04", "2026-05"]
CATEGORY_BY_MONTH = {
    "2025-12": 3,
    "2026-01": 5,
    "2026-04": 0,
    "2026-05": 4,
}
# (period, indicator) -> value; 2026-05 esi is missing on purpose so one card
# reports no_raster_data while the others carry a delta.
VALUE_BY_MONTH = {
    "2025-12": 0.41,
    "2026-01": 0.38,
    "2026-04": 0.22,
    "2026-05": 0.05,
}


def month_start(period):
    year, month = map(int, period.split("-"))
    return date(year, month, 1)


class CDIExplorerDataMixin:
    """Seeds five published months for Mhlangatane with one gap month, one
    decision-less month and one missing raster. Compose with APITestCase.
    """

    def setUp(self):
        super().setUp()
        self.administration = Administration.objects.create(
            pk=MHLANGATANE,
            name="Mhlangatane",
            region="Hhohho",
            zone="highveld",
        )
        self.uncovered = Administration.objects.create(
            pk=KWALUSENI, name="Kwaluseni", region="Manzini"
        )
        self.publications = {}
        for index, period in enumerate(PUBLISHED_MONTHS):
            self.publications[period] = self._publish(period, index)

    def _publish(self, period, index):
        covered = period in COVERED_MONTHS
        validated = (
            [
                {
                    "administration_id": MHLANGATANE,
                    "value": 2,
                    "category": CATEGORY_BY_MONTH[period],
                }
            ]
            if covered
            else []
        )
        publication = Publication.objects.create(
            cdi_geonode_id=1000 + index,
            year_month=month_start(period),
            due_date=month_start(period),
            initial_values=[],
            validated_values=validated,
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        if not covered:
            return publication
        for indicator in RasterIndicatorTypes.FieldStr:
            if period == "2026-05" and indicator == RasterIndicatorTypes.esi:
                continue
            PublicationRaster.objects.create(
                publication=publication,
                indicator=indicator,
                geonode_id=2000 + index,
                values=[
                    {
                        "administration_id": MHLANGATANE,
                        "value": VALUE_BY_MONTH[period],
                    }
                ],
            )
        return publication
