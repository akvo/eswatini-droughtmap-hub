from django.core.management.base import BaseCommand

from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.utils import (
    COMPONENT_RASTER_CATEGORIES,
    attach_component_rasters,
)


class Command(BaseCommand):
    help = (
        "Attach any missing ESI/EVI2/SM/SPI component rasters to existing "
        "publications and queue their extraction. Safe to run on a schedule: "
        "it only ever adds PublicationRaster rows and never creates, "
        "publishes or otherwise modifies a Publication."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year-month",
            dest="year_month",
            type=str,
            default=None,
            help=(
                "Limit to publications in this month (YYYY-MM). Default: all "
                "publications missing at least one component."
            ),
        )

    def handle(self, *args, **options):
        # A component is usually missing because the CDI pipeline had not
        # uploaded that month yet when the publication was created, so this
        # sweep is the retry: attach_component_rasters is idempotent and
        # skips indicators already extracted or already downloading.
        queryset = Publication.objects.all()
        year_month = options.get("year_month")
        if year_month:
            queryset = queryset.filter(year_month__startswith=year_month)

        total = 0
        for publication in queryset.iterator():
            # Cheap DB-side filter before the shared function does any
            # network work. Counts only rasters that actually have extracted
            # values: a row whose download failed has values=None and must
            # still reach attach_component_rasters, which retries it.
            extracted = publication.rasters.filter(
                values__isnull=False
            ).count()
            if extracted >= len(COMPONENT_RASTER_CATEGORIES):
                continue
            attached = attach_component_rasters(publication)
            if attached:
                total += len(attached)
                self.stdout.write(
                    f"Publication {publication.id} "
                    f"({publication.year_month}): queued {attached}"
                )

        self.stdout.write(
            self.style.SUCCESS(f"Queued {total} component raster(s).")
        )
