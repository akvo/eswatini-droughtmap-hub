import json
import logging
import time
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone
from django_q.tasks import async_task

from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from .constants import (
    DroughtCategory,
    CDIGeonodeCategory,
    GEONODE_SSL_VERIFY,
    GEONODE_REQUEST_TIMEOUT,
    PublicationStatus,
)
from .models import PublicationGeonode, PublicationRaster

logger = logging.getLogger(__name__)

TOPOJSON_PATH = "./source/eswatini.topojson"

# CDI percentile ranks only reach ~0.3 before get_category calls a month
# "Wet/normal". Seeded values are drawn from the drought end so a seeded map
# is not uniformly green — which is exactly what the removed
# fake_published_maps_seeder produced by drawing uniform(0, 100) and feeding
# it to a classifier whose whole scale is 0..1.
SEED_VALUE_RANGE = (0.02, 0.4)

BULLETIN_URL = (
    "https://www.ipcinfo.org/fileadmin/user_upload/ipcinfo/docs/"
    "IPC_Eswatini_AFI_2019June2020March.pdf"
)


def publish_seeded_publication(publication) -> bool:
    """Promote a seeded publication to published: validated_values mirror the
    extracted initial_values, due_date becomes published_at.

    One definition, two callers — the extraction hook
    (v1_jobs.job.generate_initial_cdi_values_results, the steady-state path)
    and publications_seeder's repair pass. They drifted apart before, which is
    how the "run it twice" behaviour hid (DEMO-1 D-10/D-11).

    Returns False without touching the row when there is nothing to publish.
    Empty initial_values means extraction produced nothing: publishing it
    would put a map with no categories on the National overview, which reads
    as "every Inkhundla has No Data" rather than as a failed download.
    """
    if publication.validated_values:
        return False
    if not publication.initial_values:
        logger.warning(
            f"Publication {publication.id} "
            f"(cdi_geonode_id {publication.cdi_geonode_id}) has no "
            f"initial_values; not publishing."
        )
        return False

    publication.validated_values = publication.initial_values
    publication.narrative = ""
    due_date = publication.due_date
    publication.published_at = timezone.make_aware(
        due_date
        if isinstance(due_date, datetime)
        else datetime.combine(due_date, datetime.min.time())
    )
    publication.save()
    return True


def has_active_cdi_download(publication) -> bool:
    """True when a CDI download/extraction chain is already in flight for this
    publication, so a retry would only duplicate work.

    Both halves of the chain count. Once the download finishes it is marked
    done and hands off to a SEPARATE initial_cdi_values job; checking only the
    download left that whole extraction window looking idle, so a retry during
    it would queue a second download of the same raster.

    The two halves key the publication differently — the download job stores
    `publication_id`, the extraction job stores `id` — which is why this takes
    two filters rather than one.

    A FAILED job does not count as active — same rule as
    attach_component_rasters — so a failed download is retried on the next
    pass instead of being stuck forever.
    """
    live = Jobs.objects.exclude(status=JobStatus.failed)
    return (
        live.filter(
            type=JobTypes.download_geonode_dataset,
            info__publication_id=publication.id,
        ).exists()
        or live.filter(
            type=JobTypes.initial_cdi_values,
            info__id=publication.id,
        ).exists()
    )


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


def cached_component_resource(category: str, target_month: str):
    """The cached GeoNode row for this category/month, in resource shape.

    The catalogue API and the file host fail independently (D-7): a read
    timeout on /api/v2/resources says nothing about whether the raster itself
    can be downloaded. Observed in production 2026-08-11 — the CDI download
    succeeded while every component lookup timed out, so no component raster
    attached and the review queue rendered every Inkhundla with no confidence
    band at all (the score needs the SPI raster and nothing else provides it).

    PublicationGeonode already held the row. Checking it first turns that into
    an ordinary attach.
    """
    row = (
        PublicationGeonode.objects.filter(
            category=category, year_month=f"{target_month}-01"
        )
        .exclude(download_url="")
        .exclude(download_url__isnull=True)
        .values("geonode_id", "download_url")
        .first()
    )
    if not row:
        return None
    return {"pk": row["geonode_id"], "download_url": row["download_url"]}


def cached_geonode_id(category: str, target_month: str):
    """pk of the cached GeoNode asset for this category/month, or None.

    Deliberately looser than `cached_component_resource`: this answers "which
    asset is this month's publication about", which a row with no
    download_url still answers perfectly well. Requiring one would mint a
    stand-in id for a month the list page already shows, putting two rows for
    the same month on it.
    """
    return (
        PublicationGeonode.objects.filter(
            category=category, year_month=f"{target_month}-01"
        )
        .values_list("geonode_id", flat=True)
        .first()
    )


def find_component_resource(category: str, target_month: str):
    # Cache before network: same data, and only one of the two can time out.
    cached = cached_component_resource(category, target_month)
    if cached:
        return cached

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


def requeue_cdi_extraction(publication) -> bool:
    """Re-queue the CDI download -> extract chain when `initial_values` is
    still empty.

    The create-time chain is one-shot. `download_geonode_dataset` returns
    False for any non-200, `download_geonode_dataset_results` marks the job
    failed, and nothing ever retries it — so a publication created while
    GeoNode was down keeps `initial_values = []` forever. `build_rows` derives
    one row per entry there, which is why every /reviewer/* endpoint then
    returns zero Tinkhundla and the reviewers never get their request email
    (it is sent at the *end* of the extraction chain). The component rasters
    already had this retry via `attach_component_rasters`; the CDI composite
    did not.

    Idempotent, so it is safe on a schedule: returns False without queueing
    anything when values are already extracted or a download/extraction job
    for this publication is still live. A FAILED job does not count as live,
    which is what makes the retry possible at all.
    """
    if publication.initial_values or has_active_cdi_download(publication):
        return False

    # The cached URL, not a live GeoNode resolve: PublicationGeonode is
    # already the GeoNode-independent read path (D-1), and it holds the very
    # URL the pipeline published.
    download_url = (
        PublicationGeonode.objects.filter(
            geonode_id=publication.cdi_geonode_id
        )
        .values_list("download_url", flat=True)
        .first()
    )
    if not download_url:
        logger.warning(
            f"Publication {publication.id} has no cached GeoNode "
            f"download_url for {publication.cdi_geonode_id}; skipping retry."
        )
        return False

    # Carry the original notification copy so the review-request emails that
    # never went out are sent when the chain finally completes. No risk of a
    # double send: a publication whose emails already went out has non-empty
    # initial_values and returned above.
    previous = (
        Jobs.objects.filter(
            type=JobTypes.download_geonode_dataset,
            info__publication_id=publication.id,
        )
        .order_by("-id")
        .values_list("info", flat=True)
        .first()
    ) or {}

    filename = "raster_{0}_{1}.tif".format(
        publication.cdi_geonode_id, int(time.time())
    )
    job = Jobs.objects.create(
        type=JobTypes.download_geonode_dataset,
        status=JobStatus.on_progress,
        info={
            "publication_id": publication.id,
            "filename": filename,
            # Both hooks index these unconditionally; None means "extract,
            # but send no email".
            "subject": previous.get("subject"),
            "message": previous.get("message"),
        },
    )
    job.task_id = async_task(
        "api.v1.v1_jobs.job.download_geonode_dataset",
        download_url,
        filename,
        hook="api.v1.v1_jobs.job.download_geonode_dataset_results",
    )
    job.save()
    return True


# --- Seeding helpers --------------------------------------------------------
# Used by publications_seeder to build demo/dev publication cycles. Kept here
# beside get_category, which every generated value has to pass through.


def topojson_administration_ids(path: str = TOPOJSON_PATH) -> list:
    """Administration ids straight from the topojson.

    Deliberately not a database query: the seeder must work before (or
    without) generate_administrations_seeder, and the topojson is the same
    source that command reads.
    """
    with open(path, "r") as f:
        topo_data = json.load(f)
    return [
        feature["properties"]["administration_id"]
        for group in topo_data.get("objects", {}).values()
        for feature in group.get("geometries", [])
    ]


def generate_narrative(fake) -> str:
    title = fake.sentence(nb_words=6)
    author = fake.name()
    date = fake.date()
    content = "\n".join(
        f"<p>{fake.paragraph(nb_sentences=5)}</p>" for _ in range(15)
    )
    return f"""
    <narrative>
        <h1>{title}</h1>
        <p><strong>Author:</strong> {author}</p>
        <p><strong>Date:</strong> {date}</p>
        {content}
    </narrative>
    """


def seed_values(administration_ids, rng) -> list:
    """Synthetic initial_values for one publication."""
    values = []
    for administration_id in administration_ids:
        value = rng.uniform(*SEED_VALUE_RANGE)
        values.append(
            {
                "administration_id": administration_id,
                "value": value,
                "category": get_category(value),
            }
        )
    return values


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def publish_seeded(publication, fake, rng):
    """Promote a seeded publication to published, with a narrative.

    Distinct from publish_seeded_publication above, which mirrors extracted
    values for the GeoNode chain and never invents prose.
    """
    publication.status = PublicationStatus.published
    publication.published_at = timezone.make_aware(
        _as_datetime(publication.due_date) + timedelta(days=rng.randint(1, 7))
    )
    publication.narrative = generate_narrative(fake)
    publication.bulletin_url = BULLETIN_URL
    publication.validated_values = [
        {
            "administration_id": v["administration_id"],
            "value": v["value"],
            "category": get_category(v["value"]),
        }
        for v in publication.initial_values
    ]
    publication.save()
    return publication


def seed_reviews(publication, start_date, fake, rng):
    """One Review per reviewer, completed unless the cycle is still in_review.

    suggestion_values stays None on an incomplete review: a reviewer who has
    not submitted has made no suggestions, and inventing some would show the
    validation queue an agreement it never received.
    """
    # Imported here to keep this module importable from the models layer.
    from api.v1.v1_users.constants import UserRoleTypes
    from api.v1.v1_users.models import SystemUser
    from .models import Review

    is_completed = publication.status != PublicationStatus.in_review
    due_date = _as_datetime(publication.due_date)

    reviews = []
    for reviewer in SystemUser.objects.filter(role=UserRoleTypes.reviewer):
        review, _ = Review.objects.get_or_create(
            publication=publication, user=reviewer
        )
        review.is_completed = is_completed
        review.suggestion_values = None
        if is_completed:
            review.suggestion_values = [
                _seed_suggestion(value, fake, rng)
                for value in publication.initial_values
            ]
            span = max((due_date - start_date).days, 0)
            review.completed_at = timezone.make_aware(
                start_date + timedelta(days=rng.randint(0, span))
            )
        review.save()
        reviews.append(review)
    return reviews


def _seed_suggestion(value, fake, rng) -> dict:
    suggested = value["value"]
    comment = None
    if fake.boolean():
        comment = fake.sentence(nb_words=8)
        suggested = rng.uniform(*SEED_VALUE_RANGE)
    return {
        "administration_id": value["administration_id"],
        "value": suggested,
        "comment": comment,
        "reviewed": True,
        "category": get_category(suggested),
    }
