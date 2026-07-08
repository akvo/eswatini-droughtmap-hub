"""Generic trigger evaluation shared by the wizard preview and the
`recommended-actions` endpoint.

The predicate is field-driven: it reads `dclass`, `vuln`, and every `exp[]`
condition off the stored trigger JSON and ANDs them. There is no per-activity
branching, so new or edited activities need zero code here.

Dimensions we have no honest per-administration source for yet
(`months`, IPC `ipc_phase`, `water` — see constants.UNAVAILABLE) count as
satisfied rather than being fabricated or failing every activity that uses
them. `dclass.class` and the `population/cropland/cattle` exposures evaluate
against real data (see build_dataset, added in Task 2).
"""

import csv
import logging

from api.v1.v1_activity.constants import (
    TriggerOperator,
    INDICATOR_FIELDS,
    UNAVAILABLE,
)
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)


def _satisfied(actual, op, value):
    """Apply a single operator. Caller guarantees `actual` is not None."""
    if op == TriggerOperator.gte:
        return actual >= value
    return actual <= value


def _condition_pass(actual, op, value, dimension):
    """One threshold condition. Dimensions with no source (UNAVAILABLE)
    pass unconditionally; a missing value on a real dimension fails."""
    if dimension in UNAVAILABLE:
        return True
    if actual is None:
        return False
    return _satisfied(actual, op, value)


def activity_passes(triggers, row):
    """True iff every condition in `triggers` holds for the administration
    `row`. An activity with no trigger never fires."""
    if not triggers:
        return False

    # Drought-class gate: administration category must meet the minimum.
    dclass = triggers.get("dclass") or {}
    cls = dclass.get("class")
    if cls is not None:
        cat = row.get("category")
        if cat is None or cat == DroughtCategory.none or cat < cls:
            return False
        # dclass.months is UNAVAILABLE -> no further check.

    # Vulnerability gate (IPC phase) — UNAVAILABLE, so satisfied for now.
    vuln = triggers.get("vuln")
    if vuln and not _condition_pass(
            row.get("ipc_phase"), vuln["op"], vuln["value"], "ipc_phase"):
        return False

    # Exposure gates — all AND-ed; unknown indicator fails safe.
    for cond in triggers.get("exp") or []:
        indicator = cond["indicator"]
        if indicator not in INDICATOR_FIELDS:
            return False
        if not _condition_pass(
                row.get(INDICATOR_FIELDS[indicator]),
                cond["op"], cond["value"], indicator):
            return False

    return True


# =========================================================================
# Dataset seam
# =========================================================================
# build_dataset() is the ONE place that knows where per-administration
# values come from. Today: dclass from the latest published Publication
# (real), and population/cropland/cattle from a shipped prototype CSV.
# water/ipc_phase/months have no source (see UNAVAILABLE).
# TODO(PA-2): replace this whole function with the real PA-2
# per-Inkhundla query; the predicate above stays unchanged.

logger = logging.getLogger(__name__)

_PRIORITY_CSV = "./source/priority_areas.csv"

# CSV column -> dataset row key. The authored `cropland` indicator means
# rain-fed hectares (see constants), so it maps to rainfedCropland, not
# the CSV's total `cropland`. `cattle` uses livestock (TLU) as the closest
# proxy.
_CSV_FIELDS = {
    "pop": "population",
    "rainfedCropland": "cropland",
    "livestock": "cattle",
}


def _num(raw):
    """Parse a CSV numeric cell; blank/garbage -> None."""
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value


def _latest_published_categories():
    """{administration_id: category} from the latest published
    publication, or {} when nothing is published yet."""
    pub = Publication.objects.filter(
        status=PublicationStatus.published,
        published_at__isnull=False,
    ).order_by("-year_month", "-id").first()
    if not pub:
        return {}
    values = pub.validated_values or pub.initial_values or []
    return {v["administration_id"]: v.get("category") for v in values}


def _read_priority_areas():
    """{administration_name: {population, cropland, cattle}} from the
    CSV."""
    rows = {}
    with open(_PRIORITY_CSV, newline="") as handle:
        for record in csv.DictReader(handle):
            rows[record["name"]] = {
                key: _num(record.get(column))
                for column, key in _CSV_FIELDS.items()
            }
    return rows


def build_dataset():
    """Per-administration evaluation rows keyed by administration id."""
    categories = _latest_published_categories()
    exposures = _read_priority_areas()

    dataset = {}
    for adm in Administration.objects.all():
        row = {
            "category": categories.get(adm.id),
            "population": None,
            "cropland": None,
            "cattle": None,
            "water": None,        # UNAVAILABLE
            "ipc_phase": None,    # UNAVAILABLE
            "months_active": None,
        }
        matched = exposures.get(adm.name)
        if matched is not None:
            row.update(matched)
        else:
            logger.info(
                "priority_areas.csv has no row for administration %r",
                adm.name)
        dataset[adm.id] = row
    return dataset
