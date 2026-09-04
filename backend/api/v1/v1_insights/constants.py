"""Constants for the National Overview insights surface.

Paths, palettes and the map-tab inventory live here so the modules that use
them stay about behaviour. Two pairs in particular were previously declared
twice, a file apart, and had to agree:

  - the agro-eco geometry path, read by the view that serves it
  - the CHIRPS bbox, which must match `build_chirps_normals.BBOX` or a monthly
    raster would not line up with the 30-year normals it is read against
"""
import re

# --- CHIRPS monthly rasters ------------------------------------------------

CHIRPS_BASE_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
CHIRPS_MONTHLY_DIR = "./storage/chirps_monthly"
CHIRPS_MONTHLY_FILE = "ESW_CHIRPS_precip_mm_{year_month}.tif"
# Identical to build_chirps_normals.BBOX, so a monthly raster and the normals
# it is compared against cover the same window.
CHIRPS_BBOX = (30.75, -27.5, 32.25, -25.0)

# --- Agro-ecological zone geometry -----------------------------------------

# The analysis source, in Transverse Mercator METRES (AGRO_TOPOJSON_CRS).
# `assign_administration_zones` overlays Tinkhundla against it, where a metric
# CRS is what makes the area weighting meaningful.
AGRO_TOPOJSON = "./source/eswatini-ecological_regions.topojson"
# The display copy: the same six polygons reprojected to WGS84 once and
# committed, because the reprojection is a constant. It used to be recomputed
# on every deploy into a gitignored 1.4 MB GeoJSON — a step that, when
# skipped, 404'd the tab. As quantized TopoJSON it is 173 KB and the frontend
# decodes it the same way it decodes eswatini.topojson.
AGRO_WGS84_TOPOJSON = "./source/eswatini-ecological_regions-wgs84.topojson"

# --- Administrative region geometry ----------------------------------------

# Already in degrees, so unlike the agro source it needs no reprojection at
# all — it is both the analysis source and the display copy.
REGION_TOPOJSON = "./source/eswatini-region.topojson"
# Joined on the file's own `region` property, added to carry exactly the
# values Administration.region holds: Hhohho, Lubombo, Manzini, Shiselweni.
# NAME_1 matches today, but `region` is the stated contract and the one to
# keep in step if either side is renamed.
REGION_PROPERTY = "region"

# --- Map data tabs ---------------------------------------------------------

# `year_month` indexes a file on disk, so it is validated before any path
# join rather than after. This is the only place in the feature where request
# input reaches the filesystem.
YEAR_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# `monthVarying` drives whether the frontend offers the compare selector and
# whether the month is passed to the builder. Regions and Agro-eco DO vary:
# they paint the D-class rolled up to a coarser grouping, not a static
# boundary. Only Land use and Population are genuinely time-invariant.
LAYERS = [
    {"key": "drought-class", "label": "Drought class", "monthVarying": True},
    {"key": "precipitation", "label": "Precipitation", "monthVarying": True},
    {
        "key": "esi",
        "label": "Evaporative Stress Index",
        "monthVarying": True,
    },
    {"key": "land-use", "label": "Land use", "monthVarying": False},
    {"key": "population", "label": "Population map", "monthVarying": False},
    {"key": "regions", "label": "Regions", "monthVarying": True},
    {
        "key": "agro-eco",
        "label": "Agro-ecological zones",
        "monthVarying": True,
    },
]

LAYER_LABELS = {layer["key"]: layer["label"] for layer in LAYERS}

# What each tab is actually showing, in the reader's terms. Backend-side
# because it is provenance, not styling: it names the dataset the builder
# beside it reads, and the two have to move together.
#
# The upstream dataset is cited, NOT `Indicator.source`. That column is free
# text typed at upload time and currently reads "JRBA (2026-08)" for both
# exposure layers, while the handover CSVs record WorldPop and Dynamic World.
# Repeating the stored label on a public map would publish an attribution we
# know to be wrong; the column itself is being corrected separately.
#
# `land_use_dvi_agri` is deliberately not expanded or defined here — nothing
# in the repo records what DVI-agri measures, and a public definition is not
# the place to guess.
DESCRIPTIONS = {
    "land-use": (
        "Land-use index (DVI-agri) per Inkhundla, on a 0–1 scale. Derived "
        "from Google Dynamic World satellite land cover, 22 July 2026. A "
        "static snapshot — it does not change from month to month."
    ),
    "population": (
        "Estimated residents per Inkhundla, from WorldPop gridded population "
        "summed inside each boundary. A modelled estimate rather than a "
        "census count, and a static snapshot — it does not change from month "
        "to month."
    ),
    "esi": (
        "Evaporative Stress Index for the reviewed month, as a percentile "
        "rank from 0 to 1 against the same Inkhundla's own history — darker "
        "means a higher rank. One of the four components the CDI is built "
        "from. These are ranks, not degrees: this tab was once labelled "
        "Temperature, and it does not show one."
    ),
}

# Layers `map_layers` can build. drought-class is absent on purpose: it
# already renders through Publication.validated_values with an interactive
# per-category legend this generic contract does not model.
BUILDABLE = {
    "precipitation",
    "esi",
    "land-use",
    "population",
    "regions",
    "agro-eco",
}

# Sequential ramps, low -> high. Backend-side so the legend and the values can
# never disagree about what a colour means.
#
# Regions and Agro-eco have no ramp here: they paint the D-class, whose
# palette lives in the frontend config and must have exactly one definition
# (CLAUDE.md). Their legend says `scheme: "drought"` instead.
RAMP_ESI = ["#FFFFB2", "#FED976", "#FD8D3C", "#E31A1C", "#B10026"]
RAMP_POPULATION = ["#FDE0EF", "#F1B6DA", "#DE77AE", "#C51B7D", "#8E0152"]
RAMP_LAND_USE = ["#F7FCF5", "#C7E9C0", "#74C476", "#31A354", "#006D2C"]
# Dry -> wet, so the driest Tinkhundla read pale and the wettest deep.
RAMP_PRECIPITATION = [
    "#F7FBFF",
    "#C6DBEF",
    "#6BAED6",
    "#2171B5",
    "#08306B",
]

# --- Metric cards ----------------------------------------------------------

# The metric cards' history window, in calendar months.
METRICS_HISTORY_MONTHS = 12
