"""Shared test fixtures for the CDI Explorer (INS-3)."""
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
from utils.periods import month_start, shift_period

MHLANGATANE = 4588078  # Hhohho / highveld — has published data
KWALUSENI = 2042786  # Manzini — never appears in any published month


def period_at(offset: int) -> str:
    """'YYYY-MM' `offset` months back from the current month."""
    return shift_period(timezone.now().date().strftime("%Y-%m"), -offset)


# Months back from today. The explorer window is the last 12 calendar months
# ending at the current month, so everything here lands inside it, and the
# fixture stays valid whenever it is run — hard-coded 2026 dates would drift
# out of the window as soon as the clock passed them.
#
# Shape is deliberately awkward: offsets 3 and 5 are missing entirely (no
# publication), offset 4 is published but carries no decision for this
# Inkhundla, and the latest month is missing its ESI raster. That exercises
# padding, null strip cells and no_raster_data rather than assuming them.
LATEST = 1
PREVIOUS = 2
DECISIONLESS = 4
PUBLISHED_OFFSETS = [7, 6, DECISIONLESS, PREVIOUS, LATEST]
COVERED_OFFSETS = [7, 6, PREVIOUS, LATEST]
CATEGORY_BY_OFFSET = {7: 3, 6: 5, PREVIOUS: 0, LATEST: 4}
VALUE_BY_OFFSET = {7: 0.41, 6: 0.38, PREVIOUS: 0.22, LATEST: 0.05}


class CDIExplorerDataMixin:
    """Seeds five published months for Mhlangatane inside the current window,
    with one gap, one decision-less month and one missing raster.
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
        self.publications = {
            period_at(offset): self._publish(offset, index)
            for index, offset in enumerate(PUBLISHED_OFFSETS)
        }

    def _publish(self, offset, index):
        covered = offset in COVERED_OFFSETS
        period = period_at(offset)
        publication = Publication.objects.create(
            cdi_geonode_id=1000 + index,
            year_month=month_start(period),
            due_date=month_start(period),
            initial_values=[],
            validated_values=(
                [
                    {
                        "administration_id": MHLANGATANE,
                        "value": 2,
                        "category": CATEGORY_BY_OFFSET[offset],
                    }
                ]
                if covered
                else []
            ),
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        if not covered:
            return publication
        for indicator in RasterIndicatorTypes.FieldStr:
            if offset == LATEST and indicator == RasterIndicatorTypes.esi:
                continue
            PublicationRaster.objects.create(
                publication=publication,
                indicator=indicator,
                geonode_id=2000 + index,
                values=[
                    {
                        "administration_id": MHLANGATANE,
                        "value": VALUE_BY_OFFSET[offset],
                    }
                ],
            )
        return publication
