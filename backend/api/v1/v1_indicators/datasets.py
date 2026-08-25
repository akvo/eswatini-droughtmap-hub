"""Registry of operator-maintained datasets (PA-6 D-5).

Declarative and code-owned: adding a dataset means adding a target column on
`Indicator`, which is a migration, so an admin-editable registry would only
let an operator define a dataset with nowhere to write to.

The value columns of an upload are named after `DatasetDef.field`, and that
header is what declares which datasets a file carries (D-15).
"""

from dataclasses import dataclass
from typing import Dict, Optional, Type

__all__ = [
    "DatasetDef",
    "DATASETS",
    "KEY_COLUMNS",
    "GENERIC_VALUE_COLUMN",
    "normalise_header",
    "lookup",
]

# Pre-filled by the template, never edited by the operator. `region` is
# carried for sorting against a provider's sheet and is ignored on parse.
KEY_COLUMNS = ("administration_id", "inkhundla_name", "region")

# Accepted as a value column when a file carries exactly one dataset.
GENERIC_VALUE_COLUMN = "value"


@dataclass(frozen=True)
class DatasetDef:
    slug: str
    label: str
    field: str  # Indicator column written
    dtype: Type  # int | float
    minimum: Optional[float]
    maximum: Optional[float]
    unit: str
    geonode_category: str  # phase 2; unused until the poller lands
    notes: str = ""


# Risk-score inputs first, then the SOP eligibility filters.
DATASETS: Dict[str, DatasetDef] = {
    d.slug: d
    for d in [
        DatasetDef(
            "water-demand", "Water demand", "water_demand",
            float, 0, None, "m3/year", "exposure-water-demand",
        ),
        DatasetDef(
            "cattle", "Cattle count", "cattle",
            int, 0, None, "head", "exposure-cattle",
        ),
        DatasetDef(
            "population", "Population", "population",
            int, 0, None, "people", "exposure-population",
        ),
        DatasetDef(
            "land-use-dvi-agri", "Land use DVI-agri", "land_use_dvi_agri",
            float, 0, 1, "ratio", "exposure-land-use",
        ),
        DatasetDef(
            "ipc-phase", "IPC phase", "ipc_phase",
            int, 1, 5, "phase", "vulnerability-ipc",
        ),
        DatasetDef(
            "under-five", "Children under five", "under_five",
            int, 0, None, "people", "eligibility-under-five",
        ),
        DatasetDef(
            "elderly", "Elderly population", "elderly",
            int, 0, None, "people", "eligibility-elderly",
        ),
        DatasetDef(
            "rainfed-cropland", "Rain-fed cropland", "rainfed_cropland",
            int, 0, None, "ha", "eligibility-rainfed-cropland",
        ),
        DatasetDef(
            "rangeland", "Rangeland", "rangeland",
            int, 0, None, "ha", "eligibility-rangeland",
        ),
        DatasetDef(
            "boreholes", "Boreholes", "boreholes",
            int, 0, None, "count", "eligibility-boreholes",
        ),
        DatasetDef(
            "taps", "Taps", "taps",
            int, 0, None, "count", "eligibility-taps",
        ),
    ]
}

# field name -> definition, for header discovery (D-15).
_BY_FIELD: Dict[str, DatasetDef] = {d.field: d for d in DATASETS.values()}


def normalise_header(name: str) -> str:
    """`Water Demand` and `water-demand` both reach `water_demand`.

    Mirrors the tolerance `generate_indicators_seeder._norm_name` already
    applies to Inkhundla names: operators edit these files in Excel, which
    re-cases and re-spaces headers without being asked.
    """
    # \ufeff: a byte-order mark can survive decoding and would otherwise
    # ride on the first header, silently unmatching the key column.
    text = (name or "").replace("\ufeff", "").strip().casefold()
    for char in (" ", "-", "."):
        text = text.replace(char, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def lookup(header: str) -> Optional[DatasetDef]:
    """The dataset a header names, or None if it is not a value column."""
    return _BY_FIELD.get(normalise_header(header))
