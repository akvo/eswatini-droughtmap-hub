"""Fill PublicationRaster values for the CDI component indices (DEMO-1 D-4).

Real data first — synthetic is only the last resort:

  --source path      extract from a local GeoTIFF archive, synchronously.
                     Real pct-rank rasters, no GeoNode, no worker.
  --source geonode   delegate to attach_component_rasters, which already walks
                     COMPONENT_RASTER_CATEGORIES (every CDIGeonodeCategory
                     except cdi) and queues the normal download/extract jobs.
                     Needs GeoNode credentials AND a running worker.
  --source synthetic offline fallback: percentile ranks anchored on the real
                     per-Inkhundla severity in ./source/priority_areas.csv and
                     walked month to month.

`--source auto` (the default) tries path, then geonode, then synthetic.

Sibling command: `attach_component_rasters` is the production/steady-state
path and only ever talks to GeoNode. This one exists so a demo or dev box can
fill the same column from whatever source it actually has.

PATHS: this runs inside the backend container, so --path must be a path the
container can see. `./storage` is already a persistent volume in both the dev
compose file and self-hosted, so copying the CDI pipeline output there needs
no new docker configuration:

    cp -r /path/to/output_data/GeoTiffs ./storage/geotiffs
    ./manage.py generate_rasters_seeder --source path --path ./storage/geotiffs
"""
import csv
import logging
import os
import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.v1.v1_publication.constants import (
    DEMO_RASTER_GEONODE_ID_BASE,
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationRaster,
)
from api.v1.v1_publication.raster_archive import (
    INDICATORS,
    scan_raster_archive,
)
from api.v1.v1_publication.utils import (
    COMPONENT_RASTER_CATEGORIES,
    attach_component_rasters,
    cached_geonode_id,
)

logger = logging.getLogger(__name__)

CSV_PATHS = ["./source/priority_areas.csv"]

# CDIGeonodeCategory is the GeoNode-side vocabulary ("evi2-raster-map");
# RasterIndicatorTypes is the DB-side one ("evi2"). attach_component_rasters
# bridges them with this same split, and cdi is absent by construction.
INDICATOR_BY_CATEGORY = {
    category: category.split("-")[0]
    for category in COMPONENT_RASTER_CATEGORIES
}

# --- synthetic mode only -------------------------------------------------

# Per-indicator offset from the Inkhundla's base percentile rank. The four
# indices measure different things and never sit on top of each other; without
# this the CDI-E chart draws four identical lines.
INDICATOR_OFFSET = {
    RasterIndicatorTypes.esi: 0.00,
    RasterIndicatorTypes.evi2: 0.08,
    RasterIndicatorTypes.sm: -0.05,
    RasterIndicatorTypes.spi: 0.04,
}

# How far a percentile rank may drift between consecutive months. Drought
# builds and breaks over seasons, so a large step would make every month
# independent and erase the trend the explorer exists to show.
MONTHLY_STEP = 0.06


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _norm_name(name: str) -> str:
    return (name or "").strip().casefold()


def _resolve_csv(base_dir: str):
    for path in CSV_PATHS:
        for candidate in (os.path.join(base_dir, path), path):
            if os.path.exists(candidate):
                return candidate
    return None


def _base_ranks(csv_path) -> dict:
    """{administration_id: base percentile rank} from the prototype dataset.

    `droughtScore` runs 0..1 with HIGH meaning severe drought, while a
    percentile rank runs the other way — low rank is the dry end. Hence the
    inversion; getting it backwards would paint the driest Tinkhundla as the
    wettest on every component chart.
    """
    by_name = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = _norm_name(row.get("name"))
            raw = row.get("droughtScore")
            if not name or raw in (None, "", "NA"):
                continue
            try:
                by_name[name] = 1.0 - float(raw)
            except ValueError:
                continue

    return {
        administration.id: by_name[_norm_name(administration.name)]
        for administration in Administration.objects.all()
        if _norm_name(administration.name) in by_name
    }


class Command(BaseCommand):
    help = (
        "Fill ESI/EVI2/SM/SPI PublicationRaster values from a local raster "
        "archive, GeoNode, or (last resort) a synthetic anchor."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["auto", "path", "geonode", "synthetic"],
            default="auto",
            help=(
                "Where values come from. Default: auto — path if --path is "
                "given, else geonode if configured, else synthetic."
            ),
        )
        parser.add_argument(
            "--path",
            default=None,
            help=(
                "Directory of pct-rank GeoTIFFs: either one indicator deep "
                "(with --category) or a parent of CDI/ESI/EVI2/SM/SPI. Must "
                "be readable inside the backend container; ./storage is "
                "already mounted, so copy the archive there, e.g. "
                "--path ./storage/geotiffs."
            ),
        )
        parser.add_argument(
            "--category",
            default=None,
            help=(
                "Limit --path to one indicator. Accepts either vocabulary: "
                f"{'/'.join(INDICATORS)} or "
                f"{'/'.join(sorted(INDICATOR_BY_CATEGORY))}."
            ),
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Synthetic-mode RNG seed; same seed, same values.",
        )
        parser.add_argument(
            "--published-only",
            action="store_true",
            help=(
                "Only publications already published. The CDI-E explorer "
                "reads published months only, so this matches what it serves."
            ),
        )

    def handle(self, *args, **options):
        publications = Publication.objects.order_by("year_month", "id")
        if options["published_only"]:
            publications = publications.filter(
                status=PublicationStatus.published
            )
        publications = list(publications)
        if not publications:
            self.stdout.write(
                self.style.WARNING("No publications to attach rasters to.")
            )
            return

        source = self._resolve_source(options)
        self.stdout.write(f"Component raster source: {source}")

        if source == "path":
            self.from_path(publications, options)
        elif source == "geonode":
            self.from_geonode(publications)
        else:
            self.from_synthetic(publications, options)

    def _resolve_source(self, options) -> str:
        source = options["source"]
        if source != "auto":
            if source == "path" and not options["path"]:
                raise CommandError("--source path requires --path.")
            return source
        if options["path"]:
            return "path"
        if getattr(settings, "GEONODE_BASE_URL", None):
            return "geonode"
        return "synthetic"

    def _resolve_category(self, raw):
        if raw is None:
            return None
        value = raw.strip().casefold()
        if value in INDICATOR_BY_CATEGORY:
            return INDICATOR_BY_CATEGORY[value]
        if value in INDICATORS:
            return value
        raise CommandError(
            f"Unknown --category '{raw}'. Expected one of "
            f"{sorted(INDICATORS)} or {sorted(INDICATOR_BY_CATEGORY)}."
        )

    # --- real: local archive ---------------------------------------------

    def from_path(self, publications, options):
        # Imported here rather than at module scope: it pulls rasterio and
        # geopandas, and the geonode/synthetic paths must stay usable where
        # those are not installed.
        from api.v1.v1_jobs.job import compute_zonal_values

        root = options["path"]
        if not os.path.isdir(root):
            raise CommandError(
                f"--path '{root}' is not a directory in this container. "
                f"Host paths are invisible here; copy the archive under "
                f"./storage, which is already mounted."
            )

        indicator = self._resolve_category(options["category"])
        archive = scan_raster_archive(root, indicator)
        if not archive:
            raise CommandError(
                f"No pct-rank GeoTIFFs with a YYYYMM suffix under '{root}'."
            )

        self.stdout.write(
            f"Archive: {len(archive)} raster(s) covering "
            f"{len({i for i, _ in archive})} indicator(s)."
        )

        written = 0
        missing = 0
        for publication in publications:
            period = publication.year_month.strftime("%Y-%m")
            for candidate in INDICATORS:
                if indicator and candidate != indicator:
                    continue
                filepath = archive.get((candidate, period))
                if not filepath:
                    missing += 1
                    continue
                self._write(
                    publication,
                    candidate,
                    compute_zonal_values(filepath),
                    filepath=filepath,
                )
                written += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Extracted {written} raster(s) from {root}; "
                f"{missing} month/indicator pair(s) had no matching file."
            )
        )

    # --- real: GeoNode ----------------------------------------------------

    def from_geonode(self, publications):
        """Delegate to the production path rather than reimplement it.

        attach_component_rasters already walks every CDIGeonodeCategory except
        cdi, skips indicators already extracted or with a live job, and retries
        failed ones. It queues worker jobs, so a worker must be running.
        """
        total = 0
        for publication in publications:
            attached = attach_component_rasters(publication)
            if attached:
                total += len(attached)
                self.stdout.write(
                    f"{publication.year_month}: queued {attached}"
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Queued {total} component raster(s) from GeoNode. Values "
                f"appear once the worker finishes extraction."
            )
        )

    # --- fallback: synthetic ---------------------------------------------

    def from_synthetic(self, publications, options):
        rng = random.Random(options["seed"])

        csv_path = _resolve_csv(settings.BASE_DIR)
        if csv_path is None:
            raise CommandError(
                f"Prototype CSV not found in {CSV_PATHS}; cannot anchor "
                f"synthetic component values."
            )

        base_ranks = _base_ranks(csv_path)
        if not base_ranks:
            raise CommandError(
                "No administration matched the prototype CSV. "
                "Run generate_administrations_seeder first."
            )

        # One walk per (administration, indicator) carried across months in
        # chronological order — that continuity is what makes the series a
        # trend rather than N unrelated draws.
        current = {
            (administration_id, indicator): _clamp(
                base + INDICATOR_OFFSET[indicator] + rng.gauss(0, 0.03)
            )
            for administration_id, base in base_ranks.items()
            for indicator in INDICATORS
        }

        for publication in publications:
            for indicator in INDICATORS:
                values = []
                for administration_id in sorted(base_ranks):
                    key = (administration_id, indicator)
                    current[key] = _clamp(
                        current[key] + rng.gauss(0, MONTHLY_STEP)
                    )
                    values.append(
                        {
                            "administration_id": administration_id,
                            "value": round(current[key], 4),
                        }
                    )
                self._write(publication, indicator, values)

        self.stdout.write(
            self.style.SUCCESS(
                f"Synthetic component rasters for {len(publications)} "
                f"publication(s) across {len(base_ranks)} Tinkhundla."
            )
        )

    # --- shared write -----------------------------------------------------

    def _geonode_id_for(self, publication, indicator):
        """The component asset this row is about.

        The real cached one for this indicator/month when GeoNode has it —
        the same binding the CDI publication itself now uses — and otherwise
        a stand-in derived from the publication, so re-runs stay stable
        rather than churning the column with a new id every pass.
        """
        geonode_id = cached_geonode_id(
            f"{indicator}-raster-map", publication.year_month.strftime("%Y-%m")
        )
        if geonode_id:
            return geonode_id
        return (
            DEMO_RASTER_GEONODE_ID_BASE
            + publication.id * len(INDICATORS)
            + INDICATORS.index(indicator)
        )

    def _write(self, publication, indicator, values, filepath=None):
        PublicationRaster.objects.update_or_create(
            publication=publication,
            indicator=indicator,
            defaults={
                "geonode_id": self._geonode_id_for(publication, indicator),
                "values": values,
                "extracted_at": timezone.now(),
            },
        )
        if filepath:
            logger.info(
                "Extracted %s for %s from %s",
                indicator,
                publication.year_month,
                filepath,
            )
