"""The single owner of seeded Publication rows (DEMO-1 D-2).

Replaces fake_publications_seeder and fake_published_maps_seeder, which also
created publications — three commands writing the same table with subtly
different value ranges is how the "every map is Wet/normal" bug in
fake_published_maps_seeder went unnoticed (it drew uniform(0, 100) and fed it
to a classifier whose entire scale is 0..1).

Sources, real data first:

  --source cache      the PublicationGeonode rows already in the database —
                      the same real resource list, minus the catalogue walk
  --source geonode    resource list from GeoNode; values arrive later via the
                      download -> extract -> publish chain (needs a worker)
  --source path       real pct-rank CDI GeoTIFFs from a local archive,
                      extracted synchronously. No GeoNode, no worker.
  --source synthetic  offline: topojson administrations, values drawn from the
                      drought end of the CDI scale.

`--source auto` (the default) is path -> cache -> geonode -> synthetic. `cache`
sits ahead of `geonode` because the two are the same data and only one of them
can fail: PublicationGeonode is written by the pipeline push and by
sync_publication_geonodes, and the read path has not called GeoNode since D-1.
When the catalogue is unreachable, `geonode` creates nothing (or creates rows
with empty initial_values) and the failure surfaces pages away as an empty
review queue, which is a genuinely confusing thing to debug.

Whatever the source, the publication it creates points at the GeoNode asset
for its month: `cached_geonode_id` first, and only a month with no asset at
all gets a stand-in id plus the matching `PublicationGeonode` row to go with
it. That link is what the CDI publication list joins on, so a seeded month
shows its real status there instead of offering "Start new publication" for a
publication that already exists (D-2).

Component rasters are a separate command, generate_rasters_seeder, which owns
PublicationRaster and offers the same source ladder.
"""
import random
import time
from calendar import monthrange
from datetime import datetime, timedelta

import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_q.tasks import async_task
from faker import Faker

from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from api.v1.v1_publication.constants import (
    GEONODE_SSL_VERIFY,
    GEONODE_REQUEST_TIMEOUT,
    CDIGeonodeCategory,
    DEMO_GEONODE_ID_BASE,
    PublicationStatus,
)
from api.v1.v1_publication.models import Publication, PublicationGeonode
from api.v1.v1_publication.raster_archive import scan_raster_archive
from api.v1.v1_publication.utils import (
    attach_component_rasters,
    cached_geonode_id,
    geonode_auth,
    get_category,
    has_active_cdi_download,
    publish_seeded,
    publish_seeded_publication,
    seed_reviews,
    seed_values,
    topojson_administration_ids,
)

# Stand-ins for GeoNode pks in offline test mode. Two ids keeps the historical
# fixture shape — two publications, whatever --repeat says.
TEST_GEONODE_IDS = [44, 106]


class Command(BaseCommand):
    help = (
        "Seeds Publication rows from GeoNode, a local raster archive, or "
        "synthetic values."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["auto", "cache", "geonode", "path", "synthetic"],
            default="auto",
        )
        parser.add_argument(
            "--path",
            default=None,
            help=(
                "Directory of pct-rank CDI GeoTIFFs (or a parent of "
                "CDI/ESI/...). Must be visible in this container; ./storage "
                "is already mounted, e.g. --path ./storage/geotiffs."
            ),
        )
        parser.add_argument(
            "-c", "--category",
            nargs="?",
            const=CDIGeonodeCategory.cdi,
            default=CDIGeonodeCategory.cdi,
            type=str,
            help="GeoNode category to sync (--source geonode).",
        )
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
            help="Offline fixture mode: no GeoNode, fixed ids.",
        )
        parser.add_argument(
            "-r", "--repeat", nargs="?", const=3, default=3, type=int,
            help="Months to create, doubled (historical shape).",
        )
        parser.add_argument(
            "-s", "--status",
            nargs="?",
            const=PublicationStatus.in_review,
            default=PublicationStatus.in_review,
            type=str,
            help="Status for the first --repeat publications.",
        )
        parser.add_argument(
            "-p", "--page", nargs="?", const=1, default=1, type=int,
            help="GeoNode result page to start from.",
        )
        parser.add_argument(
            "--publish-through",
            default=None,
            help=(
                "YYYY-MM. Months up to and including this are published; "
                "later ones stay in_review with initial_values populated, so "
                "an operator can walk review -> validate -> publish by hand "
                "with no GeoNode (DEMO-1 D-15). Overrides --status."
            ),
        )
        parser.add_argument(
            "--with-reviews",
            action="store_true",
            help="Also create the Review rows for the Track 2 workflow.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hard-delete existing publications first.",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="RNG seed; the same seed reproduces the same values.",
        )

    def handle(self, *args, **kwargs):
        self.rng = random.Random(kwargs["seed"])
        Faker.seed(kwargs["seed"])
        self.fake = Faker()
        self.with_reviews = kwargs["with_reviews"]
        self.publish_through = kwargs["publish_through"]

        if kwargs["reset"]:
            for publication in Publication.objects.all():
                publication.delete(hard=True)

        source = self._resolve_source(kwargs)
        self.stdout.write(f"Publication source: {source}")

        if source == "cache":
            self.from_cache(**kwargs)
        elif source == "geonode":
            self.from_geonode(**kwargs)
        elif source == "path":
            self.from_path(**kwargs)
        else:
            self.from_synthetic(**kwargs)

        self.stdout.write(
            self.style.SUCCESS("Publication data generation completed.")
        )

    def _resolve_source(self, kwargs) -> str:
        source = kwargs["source"]
        if source != "auto":
            if source == "path" and not kwargs["path"]:
                raise CommandError("--source path requires --path.")
            return source
        if kwargs["path"]:
            return "path"
        if kwargs["test"]:
            return "synthetic"
        if self._cached_resources(kwargs.get("category")):
            return "cache"
        if getattr(settings, "GEONODE_BASE_URL", None):
            return "geonode"
        return "synthetic"

    def _cached_resources(self, category=None) -> list:
        """Cached GeoNode rows shaped like the live API's resource dicts.

        Same keys `_sync_resource` and `queue_cdi_download` already read, so
        the cache is a drop-in for the catalogue walk and nothing downstream
        has to know which one it got. Newest month first, matching the live
        query's `sort[]=-date`.
        """
        queryset = PublicationGeonode.objects.filter(
            category=category or CDIGeonodeCategory.cdi,
            # A row with no download_url cannot start the extraction chain;
            # creating a publication from it would only produce the empty
            # initial_values this ordering exists to avoid.
            download_url__isnull=False,
        ).exclude(download_url="").order_by("-year_month")
        return [
            {
                "pk": row.geonode_id,
                "date": row.year_month.strftime("%Y-%m-%d"),
                "download_url": row.download_url,
            }
            for row in queryset
        ]

    def _parse_status(self, status):
        if isinstance(status, str):
            status = int(status)
        if status not in PublicationStatus.FieldStr:
            raise CommandError(
                f"Invalid status: {status}. Valid statuses are: "
                f"{', '.join(str(k) for k in PublicationStatus.FieldStr)}"
            )
        return status

    def _status_for(self, index, status, repeat, period=None):
        """Status for one seeded month.

        With --publish-through the boundary decides: everything up to it is
        published history, everything after is a live review backlog. Without
        it, the historical ladder applies — the first `repeat` months keep the
        requested status and later ones advance to in_validation, so a seeded
        database carries a cycle at every stage rather than a uniform backlog.
        """
        if self.publish_through and period:
            if period <= self.publish_through:
                return PublicationStatus.published
            return PublicationStatus.in_review
        if index + 1 > repeat and status == PublicationStatus.in_review:
            return PublicationStatus.in_validation
        return status

    def _geonode_id_for(self, period, category=CDIGeonodeCategory.cdi):
        """The GeoNode asset id this month's publication belongs to.

        Real cached asset when there is one. Otherwise a stand-in id derived
        from the month itself — never from a loop index, which re-points an
        existing stub at a different month as soon as a run covers a
        different range — plus the `PublicationGeonode` row that makes it
        resolvable.
        """
        geonode_id = cached_geonode_id(category, period)
        if geonode_id:
            return geonode_id

        year, month = (int(part) for part in period.split("-"))
        geonode_id = DEMO_GEONODE_ID_BASE + (year - 2000) * 12 + (month - 1)
        PublicationGeonode.objects.update_or_create(
            geonode_id=geonode_id,
            defaults={
                "category": category,
                "title": f"demo_cdi_pct_rank_eswatini_{year}{month:02d}",
                "year_month": f"{period}-01",
                # The marker for a stand-in row, so --clean can drop it
                # without touching a real synced resource.
                "raw": {"demo": True},
            },
        )
        return geonode_id

    def _finalise(self, publication, start_date):
        if publication.status == PublicationStatus.published:
            publish_seeded(publication, self.fake, self.rng)
        if self.with_reviews:
            seed_reviews(publication, start_date, self.fake, self.rng)

    # --- synthetic --------------------------------------------------------

    def from_synthetic(self, **kwargs):
        status = self._parse_status(kwargs["status"])
        repeat = kwargs["repeat"]
        administration_ids = topojson_administration_ids()

        # Offline fixture mode keeps its two hardcoded ids, and with them its
        # historical two-publication shape.
        months = len(TEST_GEONODE_IDS) if kwargs["test"] else repeat * 2

        current = datetime(datetime.now().year, datetime.now().month, 1)
        for index in range(months):
            last_day = monthrange(current.year, current.month)[1]
            due_date = datetime(current.year, current.month, last_day)
            previous = due_date - relativedelta(months=1)
            start_date = datetime(previous.year, previous.month, 1)
            current -= relativedelta(months=1)

            period = previous.strftime("%Y-%m")
            geonode_id = (
                TEST_GEONODE_IDS[index]
                if kwargs["test"]
                else self._geonode_id_for(period)
            )
            publication = Publication.objects.filter(
                cdi_geonode_id=geonode_id
            ).first()
            if not publication:
                publication = Publication.objects.create(
                    cdi_geonode_id=geonode_id,
                    year_month=f"{period}-01",
                    initial_values=seed_values(administration_ids, self.rng),
                    status=self._status_for(index, status, repeat, period),
                    due_date=due_date,
                    is_seeded=True,
                )
            self._finalise(publication, start_date)

        self.stdout.write(f"Synthetic: {months} publication(s).")

    # --- local raster archive --------------------------------------------

    def from_path(self, **kwargs):
        # Imported here, not at module scope: it pulls rasterio/geopandas,
        # and the other two sources must stay usable without them.
        from api.v1.v1_jobs.job import compute_zonal_values

        status = self._parse_status(kwargs["status"])
        repeat = kwargs["repeat"]
        archive = scan_raster_archive(kwargs["path"], "cdi")
        if not archive:
            raise CommandError(
                f"No CDI pct-rank GeoTIFFs under '{kwargs['path']}'."
            )

        # Newest first, so --repeat trims the oldest rather than the recent
        # months every page in scope actually reads.
        periods = sorted(
            {period for _, period in archive}, reverse=True
        )[: repeat * 2]

        for index, period in enumerate(periods):
            year, month = (int(part) for part in period.split("-"))
            start_date = datetime(year, month, 1)
            due_date = datetime(
                year, month, monthrange(year, month)[1]
            ) + relativedelta(months=1)

            values = [
                {
                    **item,
                    "category": (
                        get_category(item["value"])
                        if item["value"] is not None
                        else None
                    ),
                }
                for item in compute_zonal_values(archive[("cdi", period)])
            ]

            publication, _ = Publication.objects.get_or_create(
                cdi_geonode_id=self._geonode_id_for(period),
                defaults={
                    "year_month": f"{period}-01",
                    "initial_values": values,
                    "status": self._status_for(
                        index, status, repeat, period
                    ),
                    "due_date": due_date,
                    "is_seeded": True,
                },
            )
            self._finalise(publication, start_date)
            self.stdout.write(f"{period}: {len(values)} value(s)")

        self.stdout.write(
            self.style.SUCCESS(
                f"Extracted {len(periods)} CDI month(s) from "
                f"{kwargs['path']}."
            )
        )

    # --- GeoNode ----------------------------------------------------------

    def queue_cdi_download(self, publication, resource):
        """Queue download -> extraction -> publish for one publication.

        `is_seeder` rides in the job info all the way to
        generate_initial_cdi_values_results, which publishes the row at the
        end of the chain. That is what makes ONE run of this command enough.
        """
        filename = "raster_{0}_{1}.tif".format(
            publication.cdi_geonode_id, int(time.time())
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
        job.task_id = async_task(
            "api.v1.v1_jobs.job.download_geonode_dataset",
            resource["download_url"],
            filename,
            hook="api.v1.v1_jobs.job.download_geonode_dataset_results",
        )
        job.save()
        return job

    def resolve_pending(self, publication, resource):
        """Bring an already-created publication to published — without
        requiring another run of this command.

        Two distinct pending states, and only one of them wants a worker:
          - values extracted, never published  -> synchronous copy
          - no values at all                   -> re-queue the download chain
        """
        if publication.validated_values:
            return

        if publication.initial_values:
            if publish_seeded_publication(publication):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Published pending publication {publication.id} "
                        f"({publication.year_month})."
                    )
                )
            return

        if has_active_cdi_download(publication):
            self.stdout.write(
                f"Publication {publication.id} extraction in flight; "
                f"it will publish itself on completion."
            )
            return

        self.queue_cdi_download(publication, resource)
        self.stdout.write(
            self.style.WARNING(
                f"Publication {publication.id} had no extracted values; "
                f"re-queued its download."
            )
        )

    def from_cache(self, **kwargs):
        """Same work as from_geonode, over the cached resource list.

        Only the catalogue lookup changes. The raster download still goes to
        GeoNode (a different host, an independent failure — D-7), so this
        stays a real-data source rather than a synthetic one.
        """
        category = kwargs.get("category", CDIGeonodeCategory.cdi)
        repeat = kwargs["repeat"]
        resources = self._cached_resources(category)[: repeat * 2]
        if not resources:
            raise CommandError(
                "No PublicationGeonode rows cached for category "
                f"'{category}'. Run sync_publication_geonodes to populate "
                "the cache, or pick --source geonode / path / synthetic."
            )

        for resource in resources:
            self.stdout.write(f"Processing cached resource: {resource['pk']}")
            self._sync_resource(resource, category)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cache: {len(resources)} {category} resource(s), no "
                f"catalogue request made."
            )
        )

    def from_geonode(self, **kwargs):
        category = kwargs.get("category", CDIGeonodeCategory.cdi)
        page = kwargs.get("page", 1)

        while True:
            url = (
                "{0}/api/v2/resources"
                "?filter{{category.identifier}}={1}"
                "&filter{{subtype}}=raster&page={2}&sort[]=-date".format(
                    settings.GEONODE_BASE_URL, category, page
                )
            )
            try:
                response = requests.get(
                    url,
                    auth=geonode_auth(),
                    verify=GEONODE_SSL_VERIFY,
                    timeout=GEONODE_REQUEST_TIMEOUT,
                )
            except requests.RequestException as e:
                # Untimed and unhandled before: a GeoNode that accepted the
                # connection and stalled hung the seeder indefinitely, and a
                # refused one aborted it with a raw traceback mid-run.
                self.stdout.write(
                    self.style.ERROR(f"GeoNode unreachable on page {page}: {e}")
                )
                break
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
                self._sync_resource(resource, category)

            total_count = data.get("total", 0)
            page_size = data.get("page_size", len(resources))
            if page * page_size >= total_count or not resources:
                break
            page += 1

    def _sync_resource(self, resource, category):
        publication = Publication.objects.filter(
            cdi_geonode_id=resource["pk"]
        ).first()
        if publication:
            self.resolve_pending(publication, resource)
            self.stdout.write(
                self.style.WARNING(
                    f"Publication with cdi_geonode_id {resource['pk']} "
                    f"already exists. Skipping."
                )
            )
            if category == CDIGeonodeCategory.cdi:
                attach_component_rasters(publication)
            return

        date_str = resource.get("date", "")[:10]
        try:
            due_date = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(
                days=30
            )
        except ValueError:
            due_date = datetime.today()

        publication = Publication.objects.create(
            cdi_geonode_id=int(resource["pk"]),
            year_month=resource.get("date", "")[:7] + "-01",
            # A list, not {}: validate_json_values requires a list, and the
            # dict only ever passed because validators do not run on save().
            initial_values=[],
            due_date=due_date,
            status=PublicationStatus.published,
            is_seeded=True,
        )
        self.queue_cdi_download(publication, resource)
        if category == CDIGeonodeCategory.cdi:
            attach_component_rasters(publication)
