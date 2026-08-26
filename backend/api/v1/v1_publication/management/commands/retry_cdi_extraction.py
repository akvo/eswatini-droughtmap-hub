from django.core.management.base import BaseCommand

from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.utils import requeue_cdi_extraction


class Command(BaseCommand):
    help = (
        "Re-queue the CDI download+extraction chain for publications whose "
        "initial_values never landed (GeoNode was down or answered non-200 "
        "at creation time). Safe to run on a schedule: it only queues jobs, "
        "and never creates, publishes or otherwise modifies a Publication."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--publication",
            dest="publication",
            type=int,
            default=None,
            help=(
                "Limit to this publication id. Default: every publication "
                "with empty initial_values."
            ),
        )

    def handle(self, *args, **options):
        queryset = Publication.objects.all()
        publication_id = options.get("publication")
        if publication_id:
            queryset = queryset.filter(pk=publication_id)

        total = 0
        for publication in queryset.iterator():
            # requeue_cdi_extraction owns the "is there anything to do"
            # decision (values present / job still live), so the sweep and a
            # targeted --publication run cannot disagree about it.
            if requeue_cdi_extraction(publication):
                total += 1
                self.stdout.write(
                    f"Publication {publication.id} "
                    f"({publication.year_month}): re-queued CDI extraction"
                )

        self.stdout.write(
            self.style.SUCCESS(f"Re-queued {total} CDI extraction(s).")
        )
