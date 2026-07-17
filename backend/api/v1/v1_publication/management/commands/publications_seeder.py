import requests
import time
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django_q.tasks import async_task
from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.constants import (
    GEONODE_SSL_VERIFY,
    CDIGeonodeCategory,
    PublicationStatus,
)

# Component indicators discovered/attached alongside every CDI
# publication. CDI itself is handled by the main resource query above;
# these are the raster layers CDI is composed from.
COMPONENT_RASTER_CATEGORIES = [
    CDIGeonodeCategory.esi,
    CDIGeonodeCategory.evi2,
    CDIGeonodeCategory.sm,
    CDIGeonodeCategory.spi,
]


class Command(BaseCommand):
    help = "Generates publication data"

    def add_arguments(self, parser):
        # category
        parser.add_argument(
            "-c",
            "--category",
            nargs="?",
            const=CDIGeonodeCategory.cdi,
            default=CDIGeonodeCategory.cdi,
            type=str,
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting publication data generation...")
        self.create_publications(**kwargs)
        self.stdout.write(
            self.style.SUCCESS("Publication data generation completed.")
        )

    def create_publications(self, **kwargs):
        # Recursively fetch all pages from Geonode API
        category = kwargs.get("category", CDIGeonodeCategory.cdi)

        username = settings.GEONODE_ADMIN_USERNAME
        password = settings.GEONODE_ADMIN_PASSWORD
        page = 1
        while True:
            url = (
                "{0}/api/v2/resources"
                "?filter{{category.identifier}}={1}"
                "&filter{{subtype}}=raster&page={2}&sort[]=-date"
                .format(
                    settings.GEONODE_BASE_URL,
                    category,
                    page,
                )
            )
            response = requests.get(
                url,
                auth=(username, password),
                verify=GEONODE_SSL_VERIFY,
            )
            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to fetch page {page}: {response.status_code}"
                    )
                )
                break
            data = response.json()
            resources = data.get("resources", [])
            for resource in resources:
                self.stdout.write(f"Processing resource: {resource['pk']}")
                publication = Publication.objects.filter(
                    cdi_geonode_id=resource['pk']
                ).first()
                if publication:
                    if not publication.validated_values:
                        publication.validated_values = (
                            publication.initial_values
                        )
                        publication.narrative = ""
                        publication.published_at = timezone.make_aware(
                            publication.due_date
                        ) if isinstance(publication.due_date, datetime) \
                            else timezone.make_aware(
                                datetime.combine(
                                    publication.due_date,
                                    datetime.min.time()
                                )
                            )
                        publication.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f"Publication with cdi_geonode_id "
                            f"{resource['pk']} already exists. Skipping."
                        )
                    )
                    if category == CDIGeonodeCategory.cdi:
                        self.attach_component_rasters(publication)
                    continue

                # Create new publication if it doesn't exist
                date_str = resource.get('date', '')[:10]
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    due_date = date_obj + timedelta(days=30)
                except ValueError:
                    due_date = datetime.today()

                publication = Publication(
                    cdi_geonode_id=int(resource['pk']),
                    year_month=resource.get('date', '')[:7] + '-01',
                    initial_values={},
                    due_date=due_date,
                    status=PublicationStatus.published
                )
                publication.save()

                timestamp = int(time.time())
                filename = "raster_{0}_{1}.tif".format(
                    publication.cdi_geonode_id,
                    timestamp
                )
                job = Jobs.objects.create(
                    type=JobTypes.download_geonode_dataset,
                    status=JobStatus.on_progress,
                    info={
                        "publication_id": publication.id,
                        "filename": filename,
                        "subject": None,
                        "message": None,
                        "is_seeder": True,
                    },
                )
                hook = "download_geonode_dataset_results"
                task_id = async_task(
                    "api.v1.v1_jobs.job.download_geonode_dataset",
                    resource['download_url'],
                    filename,
                    hook=f"api.v1.v1_jobs.job.{hook}",
                )
                # Update the job with the task ID
                job.task_id = task_id
                job.save()

                if category == CDIGeonodeCategory.cdi:
                    self.attach_component_rasters(publication)
            # Pagination logic
            total_count = data.get("total", 0)
            page_size = data.get("page_size", len(resources))
            if page * page_size >= total_count or not resources:
                break
            page += 1

    def attach_component_rasters(self, publication):
        # ESI/EVI2/SM/SPI are published as their own GeoNode datasets,
        # one category each, separate from the CDI composite. For every
        # CDI publication we see (new or pre-existing), look up whichever
        # component resource matches the same year/month and queue it for
        # extraction. This runs on every seeder pass, so it doubles as a
        # one-time backfill for CDI publications that existed before
        # component rasters were tracked. Steady-state runs are the common
        # case, though, so each indicator is checked against the database
        # first and only walks the GeoNode catalogue over the network when
        # there's actually work to do (see the guard below).
        username = settings.GEONODE_ADMIN_USERNAME
        password = settings.GEONODE_ADMIN_PASSWORD
        # A publication built in this same run still holds the raw
        # "YYYY-MM-DD" string assigned to year_month (it round-trips to a
        # real date only after a DB fetch), so normalize both shapes here.
        year_month = publication.year_month
        if isinstance(year_month, str):
            year_month = datetime.strptime(year_month, "%Y-%m-%d")
        target_month = year_month.strftime("%Y-%m")

        for category in COMPONENT_RASTER_CATEGORIES:
            indicator = category.split("-")[0]

            # Guard against the network walk before doing it: if this
            # indicator already has a row that's either extracted or
            # backed by a live/pending download job, there's nothing to
            # do. A previously FAILED job does NOT count as active, so a
            # failed download gets retried on the next pass instead of
            # being stuck forever.
            existing = PublicationRaster.objects.filter(
                publication=publication, indicator=indicator
            ).first()
            has_active_job = existing and Jobs.objects.filter(
                type=JobTypes.download_geonode_dataset,
                info__publication_raster_id=existing.id,
            ).exclude(status=JobStatus.failed).exists()
            if existing and (existing.values is not None or has_active_job):
                continue

            resource = self.find_component_resource(
                category, target_month, username, password
            )
            if not resource:
                continue

            raster, _ = PublicationRaster.objects.get_or_create(
                publication=publication,
                indicator=indicator,
                defaults={"geonode_id": int(resource["pk"])},
            )

            timestamp = int(time.time())
            filename = "raster_{0}_{1}_{2}.tif".format(
                publication.id, indicator, timestamp
            )
            job = Jobs.objects.create(
                type=JobTypes.download_geonode_dataset,
                status=JobStatus.on_progress,
                info={
                    "publication_raster_id": raster.id,
                    "filename": filename,
                },
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.download_geonode_dataset",
                resource["download_url"],
                filename,
                hook="api.v1.v1_jobs.job.download_indicator_dataset_results",
            )
            job.task_id = task_id
            job.save()

    def find_component_resource(
        self, category, target_month, username, password
    ):
        # Same paginated GeoNode query as the CDI discovery loop above,
        # but stops as soon as a resource in the target month is found
        # rather than walking every page unconditionally.
        page = 1
        while True:
            url = (
                "{0}/api/v2/resources"
                "?filter{{category.identifier}}={1}"
                "&filter{{subtype}}=raster&page={2}&sort[]=-date"
                .format(settings.GEONODE_BASE_URL, category, page)
            )
            response = requests.get(
                url,
                auth=(username, password),
                verify=GEONODE_SSL_VERIFY,
            )
            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to fetch {category} page {page}: "
                        f"{response.status_code}"
                    )
                )
                return None
            data = response.json()
            resources = data.get("resources", [])
            for resource in resources:
                if resource.get("date", "")[:7] == target_month:
                    return resource
            total_count = data.get("total", 0)
            page_size = data.get("page_size", len(resources))
            if page * page_size >= total_count or not resources:
                return None
            page += 1
