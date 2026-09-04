"""National Overview map data tabs — one layer contract for every tab (INS-3).

Sibling of `services.py` rather than part of it: this is presentation config
for one page (colour ramps, legends, render modes), and services.py is already
past the file-size guideline. Both compose across v1_publication and
v1_indicators, which is why neither belongs beside a single model.

Each tab is described by a payload carrying a ``type`` discriminator, its data,
and its legend. The legend rides in the same response deliberately: there is no
way for a caller to render a layer without the legend that explains it.

Render modes:
    choropleth  per-Inkhundla values painted onto the existing topojson
    image       a pre-coloured PNG + bounds for a Leaflet ImageOverlay
    vector      a URL to a geometry set that is NOT the Tinkhundla polygons
    empty       a valid "we have no data for this month" answer, not a 404

``drought-class`` is deliberately absent. It already renders through
``Publication.validated_values`` with an interactive per-category legend this
generic contract does not model, and rewriting a working tab to fit a uniform
shape would be risk without user-visible gain.
"""
import logging
import os
from collections import defaultdict

from django.conf import settings

from api.v1.v1_indicators.models import Indicator
from api.v1.v1_insights.chirps_extract import read_sidecar
from api.v1.v1_insights.constants import (
    BUILDABLE,
    DESCRIPTIONS,
    CHIRPS_MONTHLY_DIR,
    CHIRPS_MONTHLY_FILE,
    LAYER_LABELS,
    LAYERS,
    RAMP_ESI,
    RAMP_LAND_USE,
    RAMP_POPULATION,
    RAMP_PRECIPITATION,
    REGION_PROPERTY,
)
from api.v1.v1_insights.drought_aggregation import grouped_drought
from api.v1.v1_publication.constants import (
    AGRO_LEVEL1_ZONES,
    ZONE_LABELS,
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationRaster,
)

logger = logging.getLogger(__name__)


def chirps_monthly_path(year_month: str) -> str:
    """Absolute path to one month's CHIRPS window. Caller must validate."""
    return os.path.join(
        settings.BASE_DIR,
        CHIRPS_MONTHLY_DIR,
        CHIRPS_MONTHLY_FILE.format(year_month=year_month),
    )


def empty_layer(key: str, reason: str) -> dict:
    """A month we genuinely have no data for. 200, not 404."""
    return {
        "key": key,
        "label": LAYER_LABELS.get(key, key),
        "type": "empty",
        "reason": reason,
    }


def continuous_legend(values, unit, colors, decimals=2):
    """Min/max endpoints for a continuous ramp.

    Endpoints come from the data actually being painted, not a fixed scale: an
    ESI month that never leaves 0.4-0.6 should still use the whole ramp rather
    than rendering as one flat colour.
    """
    numbers = [v for v in values if v is not None]
    if not numbers:
        return None
    low, high = min(numbers), max(numbers)
    if low == high:
        # A degenerate range would make the frontend divide by zero. Widen it
        # so the single value lands mid-ramp instead.
        low, high = low - 1, high + 1
    return {
        "unit": unit,
        "min": round(low, decimals),
        "max": round(high, decimals),
        "continuous": True,
        "colors": colors,
    }


def _indicator_rows(column):
    """([{administration_id, value}], provisional, sources) for one column.

    `is_placeholder` is read rather than assumed: the seeder has always set it
    True on the CSV-backed rows, and PA-4 will set it False. Reading it is what
    makes the provisional badge self-clearing.
    """
    rows = list(
        Indicator.objects.filter(**{f"{column}__isnull": False}).values_list(
            "administration_id", column, "is_placeholder", "source"
        )
    )
    data = [
        {"administration_id": adm_id, "value": value}
        for adm_id, value, _, _ in rows
    ]
    provisional = any(is_placeholder for _, _, is_placeholder, _ in rows)
    sources = sorted({source for _, _, _, source in rows if source})
    return data, provisional, sources


def build_population() -> dict:
    data, provisional, sources = _indicator_rows("population")
    if not data:
        return empty_layer("population", "No population data seeded.")
    meta = {
        "source": ", ".join(sources) or None,
        "asOf": None,
        "description": DESCRIPTIONS["population"],
    }
    if provisional:
        meta["provisional"] = True
        meta["note"] = (
            "Source dataset and vintage are not recorded. "
            "Values are indicative."
        )
    return {
        "key": "population",
        "label": LAYER_LABELS["population"],
        "type": "choropleth",
        "data": data,
        "legend": continuous_legend(
            [d["value"] for d in data], "people", RAMP_POPULATION, decimals=0
        ),
        "meta": meta,
    }


def build_land_use() -> dict:
    data, provisional, sources = _indicator_rows("land_use_dvi_agri")
    if not data:
        return empty_layer("land-use", "No land-use data seeded.")
    meta = {
        "source": ", ".join(sources) or None,
        "asOf": None,
        "description": DESCRIPTIONS["land-use"],
    }
    if provisional:
        meta["provisional"] = True
        # Two different warnings. The badge says "provisional"; this says the
        # values barely differ, which a near-flat map cannot communicate on
        # its own.
        meta["note"] = (
            "Provisional: derivation method is not fully recorded, and "
            "values vary little between Tinkhundla — read differences with "
            "caution."
        )
    return {
        "key": "land-use",
        "label": LAYER_LABELS["land-use"],
        "type": "choropleth",
        "data": data,
        "legend": continuous_legend(
            [d["value"] for d in data], "DVI-agri (0-1)", RAMP_LAND_USE
        ),
        "meta": meta,
    }


def build_esi(year_month: str = None) -> dict:
    """ESI from the values the worker already extracted per Inkhundla.

    No GeoNode call: `generate_indicator_values` has already reduced the
    component raster to ~59 {administration_id, value} rows.
    """
    queryset = PublicationRaster.objects.filter(
        indicator=RasterIndicatorTypes.esi,
        publication__status=PublicationStatus.published,
        values__isnull=False,
    )
    if year_month:
        year, month = year_month.split("-")
        queryset = queryset.filter(
            publication__year_month__year=int(year),
            publication__year_month__month=int(month),
        )
    raster = queryset.order_by(
        "-publication__year_month", "-publication_id"
    ).first()
    if not raster or not raster.values:
        return empty_layer(
            "esi",
            "No Evaporative Stress Index raster has been extracted for "
            "this month.",
        )

    data = [
        {
            "administration_id": row.get("administration_id"),
            "value": row.get("value"),
        }
        for row in raster.values
        if row.get("value") is not None
    ]
    if not data:
        return empty_layer("esi", "The extracted ESI raster has no values.")

    return {
        "key": "esi",
        "label": LAYER_LABELS["esi"],
        "type": "choropleth",
        "data": data,
        # Percentile rank, NOT degrees. Saying so is load-bearing on a public
        # page: this tab used to be labelled "Temperature".
        "legend": continuous_legend(
            [d["value"] for d in data], "percentile rank", RAMP_ESI
        ),
        "meta": {
            "source": "era5_esi_1mn (CDI component raster)",
            "asOf": raster.publication.year_month.strftime("%Y-%m-%d"),
            "description": DESCRIPTIONS["esi"],
        },
    }


def build_regions(year_month: str = None) -> dict:
    """Drought class aggregated to the four administrative regions.

    Drawn on the real region polygons, the same way agro-eco is. It used to
    paint the verdict onto all 59 Tinkhundla instead: a region read as one
    colour, but the boundaries on screen were still Inkhundla boundaries, so
    the Regions tab and the default tab drew the same map in different
    palettes. The region outlines were nowhere on it.
    """
    rows = list(
        Administration.objects.filter(region__isnull=False)
        .exclude(region="")
        .values_list("id", "region")
    )
    if not rows:
        return empty_layer("regions", "No administrative regions seeded.")

    groups = defaultdict(list)
    for adm_id, region in rows:
        groups[region].append(adm_id)

    drought, publication = grouped_drought(groups, year_month)
    if not drought:
        return empty_layer(
            "regions", "No published drought map to aggregate by region."
        )

    return {
        "key": "regions",
        "label": LAYER_LABELS["regions"],
        "type": "vector",
        "url": "/api/v1/insights/geo/regions",
        "property": REGION_PROPERTY,
        # Keyed by the geometry's own `region` property, so the join never
        # depends on the file's feature order.
        "data": [
            {
                "key": region,
                "label": region,
                "value": value,
                "confidence": confidence,
            }
            for region, (value, confidence) in sorted(drought.items())
        ],
        # No colours: the D-class palette lives in the frontend config and
        # must have exactly one definition (CLAUDE.md).
        "legend": {"scheme": "drought"},
        "meta": {
            "source": "Modal drought class per region",
            "asOf": (
                publication.year_month.strftime("%Y-%m-%d")
                if publication
                else None
            ),
        },
    }


def build_agro_eco(year_month: str = None) -> dict:
    """Drought class aggregated to the six agro-ecological zones.

    Drawn on the real ecological-region polygons rather than Tinkhundla
    coloured by their dominant zone: 40 of 59 span more than one zone (see
    `assign_administration_zones`), so the Inkhundla version would draw
    boundaries that do not exist. The geometry loads from its own endpoint
    because it is ~150 KB and most visitors never open this tab.
    """
    rows = list(
        Administration.objects.filter(zone__isnull=False)
        .exclude(zone="")
        .values_list("id", "zone")
    )
    groups = defaultdict(list)
    for adm_id, zone in rows:
        groups[zone].append(adm_id)

    drought, publication = grouped_drought(groups, year_month)

    return {
        "key": "agro-eco",
        "label": LAYER_LABELS["agro-eco"],
        "type": "vector",
        "url": "/api/v1/insights/geo/agro-eco",
        "property": "LEVEL1",
        # Keyed by the topojson's own LEVEL1 code so the frontend joins on a
        # property the geometry actually carries.
        "data": [
            {
                "key": level1,
                "label": ZONE_LABELS[zone],
                "value": drought.get(zone, (None, 0))[0],
                "confidence": drought.get(zone, (None, 0))[1],
            }
            for level1, zone in AGRO_LEVEL1_ZONES.items()
        ],
        "legend": {"scheme": "drought"},
        "meta": {
            "source": "Modal drought class per agro-ecological zone",
            "asOf": (
                publication.year_month.strftime("%Y-%m-%d")
                if publication
                else None
            ),
            # Worth stating: a zone's verdict is built from the Tinkhundla
            # whose DOMINANT zone it is, then painted on the true polygon.
            "note": (
                "Zone values are aggregated from Tinkhundla by their "
                "dominant zone; most Tinkhundla span more than one zone."
            ),
        },
    }


def build_precipitation(year_month: str = None) -> dict:
    """CHIRPS rainfall for one month, averaged per Inkhundla.

    Was a pixel overlay. At national zoom that rendered as an unlabelled
    rectangle covering the bounding box — including chunks of two neighbouring
    countries — with nothing to locate it against, so it read as texture
    rather than rainfall. The zonal mean on the Inkhundla polygons is legible,
    hoverable and consistent with the rest of the card.
    """
    if not year_month:
        publication = (
            Publication.objects.filter(status=PublicationStatus.published)
            .order_by("-year_month", "-id")
            .first()
        )
        if not publication:
            return empty_layer(
                "precipitation", "No published month to show rainfall for."
            )
        year_month = publication.year_month.strftime("%Y-%m")

    path = chirps_monthly_path(year_month)
    if not os.path.exists(path):
        # A missing file is the normal state until fetch_chirps_monthly has
        # run for this month, so it degrades rather than erroring.
        return empty_layer(
            "precipitation",
            f"No CHIRPS rainfall raster stored for {year_month}.",
        )

    data = read_sidecar(path)
    if not data:
        # The raster is stored but not yet reduced — a fetch from before this
        # tab became a choropleth. Re-running fetch_chirps_monthly --force
        # writes the extract.
        return empty_layer(
            "precipitation",
            f"Rainfall for {year_month} has not been extracted per "
            "Inkhundla yet.",
        )

    return {
        "key": "precipitation",
        "label": LAYER_LABELS["precipitation"],
        "type": "choropleth",
        "data": data,
        "legend": continuous_legend(
            [row["value"] for row in data], "mm", RAMP_PRECIPITATION,
            decimals=1,
        ),
        "meta": {
            "source": "CHIRPS v2.0 africa_monthly",
            "asOf": f"{year_month}-01",
            "attribution": "Funk et al. (2015), UCSB Climate Hazards Center",
        },
    }


BUILDERS = {
    "precipitation": build_precipitation,
    "esi": build_esi,
    "land-use": build_land_use,
    "population": build_population,
    "regions": build_regions,
    "agro-eco": build_agro_eco,
}

# Builders that take a month. Kept in step with the `monthVarying` flags
# above: a layer advertised as month-varying whose builder ignores the month
# would silently pin the map to the latest publication.
_MONTHLY = {
    layer["key"] for layer in LAYERS if layer["monthVarying"]
} & BUILDABLE


def build_layer(key: str, year_month: str = None):
    """Dispatch to one layer builder. Returns None for an unknown key."""
    builder = BUILDERS.get(key)
    if builder is None:
        return None
    return builder(year_month) if key in _MONTHLY else builder()
