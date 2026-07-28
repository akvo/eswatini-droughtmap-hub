import logging
import time
from datetime import datetime

import requests
from django.conf import settings
from django_q.tasks import async_task

from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from .constants import (
    DroughtCategory,
    CDIGeonodeCategory,
    GEONODE_SSL_VERIFY,
    GEONODE_REQUEST_TIMEOUT,
)
from .models import PublicationRaster

logger = logging.getLogger(__name__)


def get_category(value: float):
    value = round(value, 3)
    if (value < 0):
        return DroughtCategory.none
    if (value >= 0 and value <= 0.02):
        return DroughtCategory.d4
    if (value > 0.02 and value <= 0.05):
        return DroughtCategory.d3
    if (value > 0.05 and value <= 0.1):
        return DroughtCategory.d2
    if (value > 0.1 and value <= 0.2):
        return DroughtCategory.d1
    if (value > 0.2 and value <= 0.3):
        return DroughtCategory.d0
    return DroughtCategory.normal


# Component indicators discovered/attached alongside every CDI publication.
# CDI itself is handled by the caller; these are the raster layers CDI is
# composed from.
COMPONENT_RASTER_CATEGORIES = [
    CDIGeonodeCategory.esi,
    CDIGeonodeCategory.evi2,
    CDIGeonodeCategory.sm,
    CDIGeonodeCategory.spi,
]


def geonode_auth():
    return (settings.GEONODE_ADMIN_USERNAME, settings.GEONODE_ADMIN_PASSWORD)


def as_target_month(year_month) -> str:
    # A publication built in the same process still holds the raw
    # "YYYY-MM-DD" string assigned to year_month (it round-trips to a real
    # date only after a DB fetch), so normalize both shapes here.
    if isinstance(year_month, str):
        year_month = datetime.strptime(year_month[:10], "%Y-%m-%d")
    return year_month.strftime("%Y-%m")


def find_component_resource(category: str, target_month: str):
    # Paginated GeoNode catalogue query that stops as soon as a resource in
    # the target month is found rather than walking every page.
    page = 1
    while True:
        url = (
            "{0}/api/v2/resources"
            "?filter{{category.identifier}}={1}"
            "&filter{{subtype}}=raster&page={2}&sort[]=-date"
            .format(settings.GEONODE_BASE_URL, category, page)
        )
        try:
            response = requests.get(
                url,
                auth=geonode_auth(),
                verify=GEONODE_SSL_VERIFY,
                timeout=GEONODE_REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            # GeoNode being unreachable must never propagate: for the
            # create-time path (D-6) this runs in a worker alongside the CDI
            # chain, and for the preview endpoint (D-8) an unavailable
            # catalogue simply means "unknown", not a failed request.
            logger.error(f"GeoNode request failed for {category}: {e}")
            return None
        if response.status_code != 200:
            logger.error(
                f"Failed to fetch {category} page {page}: "
                f"{response.status_code}"
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


def discover_components(target_month: str) -> list:
    # Read-only availability lookup backing the create-form preview (D-8).
    # Advisory only: the attach job re-reads the catalogue later and stays
    # the source of truth.
    results = []
    for category in COMPONENT_RASTER_CATEGORIES:
        resource = find_component_resource(category, target_month)
        results.append({
            "key": category.split("-")[0],
            "label": CDIGeonodeCategory.FieldStr[category],
            "available": bool(resource),
            "geonode_id": int(resource["pk"]) if resource else None,
        })
    return results


def attach_component_rasters(publication) -> list:
    # ESI/EVI2/SM/SPI are published as their own GeoNode datasets, one
    # category each, separate from the CDI composite. For every CDI
    # publication (new or pre-existing), look up whichever component resource
    # matches the same year/month and queue it for extraction.
    #
    # Every call is idempotent, so this doubles as the historical backfill
    # when run from the seeder and as a retry for anything that failed
    # earlier. Steady-state runs are the common case, though, so each
    # indicator is checked against the database first and only walks the
    # GeoNode catalogue over the network when there's actually work to do.
    target_month = as_target_month(publication.year_month)
    attached = []

    for category in COMPONENT_RASTER_CATEGORIES:
        indicator = category.split("-")[0]

        # Guard against the network walk before doing it: if this indicator
        # already has a row that's either extracted or backed by a
        # live/pending download job, there's nothing to do. A previously
        # FAILED job does NOT count as active, so a failed download gets
        # retried on the next pass instead of being stuck forever.
        existing = PublicationRaster.objects.filter(
            publication=publication, indicator=indicator
        ).first()
        has_active_job = existing and Jobs.objects.filter(
            type=JobTypes.download_geonode_dataset,
            info__publication_raster_id=existing.id,
        ).exclude(status=JobStatus.failed).exists()
        if existing and (existing.values is not None or has_active_job):
            continue

        resource = find_component_resource(category, target_month)
        if not resource:
            # Usually just a timing gap — the CDI pipeline has not uploaded
            # this month yet. The next scheduled seeder pass retries it
            # (D-7); no row is persisted for an absent raster.
            logger.info(
                f"No {category} resource for {target_month}; skipping."
            )
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
        attached.append(indicator)

    return attached
