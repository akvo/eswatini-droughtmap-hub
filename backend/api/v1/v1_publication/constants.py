from enum import Enum

GEONODE_SSL_VERIFY = True
# (connect, read) timeout in seconds for outbound GeoNode requests so a slow
# or unresponsive upstream can never hang the request thread indefinitely.
GEONODE_REQUEST_TIMEOUT = (10, 60)

# ponytail: SPI/LST have no backend source yet — fixed placeholder per row.
MOCK_STATIONS = {"spi": 0.49, "lst": 2.0, "is_mock": True}
BANDS = ["low", "medium", "high"]


class PublicationStatus:
    in_review = 1
    in_validation = 2
    published = 3

    FieldStr = {
        in_review: "In Review",
        in_validation: "In Validation",
        published: "Published",
    }


class DroughtCategory:
    normal = 0
    d0 = 1
    d1 = 2
    d2 = 3
    d3 = 4
    d4 = 5
    none = -9999

    FieldStr = {
        normal: "Wet/normal conditions",
        d0: "D0 Abnormally Dry",
        d1: "D1 Moderate Drought",
        d2: "D2 Severe Drought",
        d3: "D3 Extreme Drought",
        d4: "D4 Exceptional Drought",
        none: "No Data",
    }


# Everything an admin may validate an Inkhundla to. Excludes `none` (-9999):
# "No Data" is raster output where the CDI had no signal, never a decision
# an admin hands down, and a published map must not carry it.
VALIDATABLE_CATEGORIES = [
    (key, label)
    for key, label in DroughtCategory.FieldStr.items()
    if key != DroughtCategory.none
]


def is_validated(category):
    """A real, admin-assigned D-class. Not null, and not No Data.

    ``DroughtCategory.none`` (-9999) is what the raster emits where it had no
    signal; it is never a decision an admin hands down, and a published map
    must not carry it. Lives here, beside the enum it interprets, so the row
    status, the publish gate and the serialized category all share one
    definition without any of them importing each other.
    """
    return category is not None and category != DroughtCategory.none


class ValidationStatus:
    """Row status on the admin validation queue.

    A partition — every Inkhundla is exactly one of these — so the three
    counts sum to the total and each summary card equals the row count behind
    its matching tab. Computed per request, never stored.
    """

    ready = "ready"
    awaiting = "awaiting"
    validated = "validated"

    FieldStr = {
        ready: "Ready for validation",
        awaiting: "Awaits reviews",
        validated: "Validated this period",
    }


class ConsensusBand:
    """Bands over the consensus score.

    The cut-points are multiples of 20 because that is where the score means
    something provable: `consensus < 100 - 20*s` implies at least two
    reviewers are more than `s` D-classes apart. So `< 60` certifies a
    disagreement wider than two D-classes and `< 40` wider than three. Round
    numbers borrowed from modal-share intuition would not carry that.
    """

    high = "high"
    moderate = "moderate"
    low = "low"
    none = "none"

    FieldStr = {
        high: "High consensus",
        moderate: "Moderate consensus",
        low: "Low consensus",
        none: "No consensus",
    }

    # (floor, band), highest floor first.
    THRESHOLDS = ((80, high), (60, moderate), (40, low))


# Consensus is the mean absolute deviation of the submitted D-classes from
# their median, normalized against the worst case: half the panel at each end
# of the scale puts the median at the midpoint, giving a mean deviation of
# span/2. Distance-aware, so [1,2] and [1,5] do not score alike.
DROUGHT_SCALE_SPAN = DroughtCategory.d4 - DroughtCategory.normal
CONSENSUS_MAX_DEV = DROUGHT_SCALE_SPAN / 2

# Strictly more than this many distinct D-classes on one Inkhundla counts as
# "high disagreement" on the summary cards — exactly 3 does not qualify.
DISAGREEMENT_THRESHOLD = 3

# Agreement is a statement about two or more people. Below this, an Inkhundla
# has no consensus score and belongs to neither agreement filter: one reviewer
# has not agreed with anyone, and calling that 100% would let a whole
# publication be bulk-validated on a single person's word (D-1, D-9).
MIN_SUBMISSIONS_FOR_AGREEMENT = 2

# Distinct Technical Working Groups a new publication's reviewer panel must
# span. Two reviewers from the same TWG still leave `reviewers_required` at 1,
# so every Inkhundla would reach "ready" on one institution's response — the
# floor is on TWGs, not headcount, because that is the unit the workflow
# counts in (D-10).
MIN_TWGS_PER_PUBLICATION = 2


class AgreementFilter:
    """Cross-cutting filter over how far apart the reviewers are.

    Deliberately NOT a partition, and deliberately not complements of each
    other: `disagreement` matches the "High disagreement" summary card
    (> DISAGREEMENT_THRESHOLD distinct classes) so clicking the card cannot
    show a different number than the card claims. Rows with 2..3 distinct
    classes are in neither — mild disagreement, still a human's job (D-2).
    """

    undisputed = "undisputed"
    disagreement = "disagreement"

    FieldStr = {
        undisputed: "Non-disputed only",
        disagreement: "High disagreement",
    }


# Bulk-validated decisions get generated reasoning rather than a null, so a
# history entry never reads as an omission. Fixed prefix so an audit can find
# every one of them with a single LIKE (D-8).
BULK_REASONING_PREFIX = "Bulk-validated:"


class CDIGeonodeCategory:
    cdi = "cdi-raster-map"
    spi = "spi-raster-map"
    esi = "esi-raster-map"
    evi2 = "evi2-raster-map"
    sm = "sm-raster-map"

    FieldStr = {
        cdi: "CDI Raster Map",
        spi: "SPI Raster Map",
        esi: "ESI Raster Map",
        evi2: "EVI2 Raster Map",
        sm: "SM Raster Map",
    }


class DroughtCategoryColor:
    normal = 0
    d0 = 1
    d1 = 2
    d2 = 3
    d3 = 4
    d4 = 5

    FieldStr = {
        normal: "#b9f8cf",
        d0: "#ffff00",
        d1: "#fbd47f",
        d2: "#ffaa00",
        d3: "#e60000",
        d4: "#730000",
    }


class ExportMapTypes:
    geojson = "geojson"
    shapefile = "shapefile"
    png = "png"
    svg = "svg"

    FieldStr = {
        geojson: "GeoJSON",
        shapefile: "Shapefile",
        png: "PNG",
        svg: "SVG",
    }


class FilterStatus:
    all = "all"
    not_yet_started = "not_yet_started"
    pending = "pending"
    completed = "completed"

    FieldStr = {
        all: "All",
        not_yet_started: "Not yet started",
        pending: "Pending",
        completed: "Completed",
    }


class RasterIndicatorTypes:
    esi = "esi"
    evi2 = "evi2"
    sm = "sm"
    spi = "spi"

    FieldStr = {
        esi: "ESI percentile rank",
        evi2: "EVI2 percentile rank",
        sm: "SM percentile rank",
        spi: "SPI percentile rank",
    }

    @classmethod
    def choices(cls):
        return list(cls.FieldStr.items())


class AdministrationZones(Enum):
    """The six Eswatini agro-ecological zones.

    These mirror the `LEVEL1` classes in
    ``source/eswatini-ecological_regions.topojson``, which is the authoritative
    layer. An earlier four-zone model merged Upper/Lower Middleveld and
    Western/Eastern Lowveld, which no source actually distinguishes that way.
    """

    HIGHVELD = "highveld"
    UPPER_MIDDLEVELD = "upper_middleveld"
    LOWER_MIDDLEVELD = "lower_middleveld"
    WESTERN_LOWVELD = "western_lowveld"
    EASTERN_LOWVELD = "eastern_lowveld"
    LUBOMBO_RANGE = "lubombo_range"

    @classmethod
    def choices(cls):
        return [(tag.value, ZONE_LABELS[tag.value]) for tag in cls]

    @classmethod
    def values(cls):
        return [tag.value for tag in cls]


# Display labels — `name.capitalize()` cannot render "Upper Middleveld".
ZONE_LABELS = {
    AdministrationZones.HIGHVELD.value: "Highveld",
    AdministrationZones.UPPER_MIDDLEVELD.value: "Upper Middleveld",
    AdministrationZones.LOWER_MIDDLEVELD.value: "Lower Middleveld",
    AdministrationZones.WESTERN_LOWVELD.value: "Western Lowveld",
    AdministrationZones.EASTERN_LOWVELD.value: "Eastern Lowveld",
    AdministrationZones.LUBOMBO_RANGE.value: "Lubombo Range",
}

# `LEVEL1` code in the agro-ecological topojson -> zone value.
AGRO_LEVEL1_ZONES = {
    "HV": AdministrationZones.HIGHVELD.value,
    "MU": AdministrationZones.UPPER_MIDDLEVELD.value,
    "ML": AdministrationZones.LOWER_MIDDLEVELD.value,
    "LW": AdministrationZones.WESTERN_LOWVELD.value,
    "LE": AdministrationZones.EASTERN_LOWVELD.value,
    "LR": AdministrationZones.LUBOMBO_RANGE.value,
}

# The agro topojson carries no CRS. Its coordinates are metres in a Transverse
# Mercator centred on 31E (verified: reprojecting to WGS84 reproduces the
# Tinkhundla extent to ~0.004 deg).
AGRO_TOPOJSON_CRS = (
    "+proj=tmerc +lat_0=0 +lon_0=31 +k=1 +x_0=0 +y_0=0 "
    "+datum=WGS84 +units=m +no_defs"
)
