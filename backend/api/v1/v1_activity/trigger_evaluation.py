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

from api.v1.v1_activity.constants import (
    TriggerOperator,
    INDICATOR_FIELDS,
    UNAVAILABLE,
)
from api.v1.v1_publication.constants import DroughtCategory


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
