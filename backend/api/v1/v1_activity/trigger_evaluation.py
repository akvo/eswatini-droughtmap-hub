"""Generic trigger evaluation shared by the wizard preview and the
`recommended-actions` endpoint.

The predicate is field-driven: it reads `dclass`, `vuln`, `exp`, and `risk`
conditions off the stored trigger JSON and ANDs them.

Now backed by the real per-Inkhundla `Indicator` DB table (PA-2 / v2 redesign).
"""

import logging

from api.v1.v1_activity.constants import (
    TriggerOperator,
    EXPOSURE_INDICATORS,
    UNAVAILABLE,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.constants import (
    HAZARD_RESCALE,
    IPC_RESCALE,
    RISK_BANDS,
    EXPOSURE_SUBINDICATORS,
)
from api.v1.v1_publication.constants import DroughtCategory

logger = logging.getLogger(__name__)

# Numeric rank for risk_class comparison (higher number = higher risk)
_RISK_CLASS_RANK = {
    "Low": 1,
    "Moderate": 2,
    "High": 3,
    "Very High": 4,
}

_DROUGHT_CATEGORY_TO_HAZARD_KEY = {
    DroughtCategory.none: "None",
    DroughtCategory.d0: "D0",
    DroughtCategory.d1: "D1",
    DroughtCategory.d2: "D2",
    DroughtCategory.d3: "D3",
    DroughtCategory.d4: "D4",
}


def _condition_pass(actual, op, value, dimension):
    """One threshold condition. Dimensions with no source (UNAVAILABLE)
    pass unconditionally; a missing value on a real dimension fails."""
    if dimension in UNAVAILABLE:
        return True
    if actual is None:
        return False
    if op == TriggerOperator.gte:
        return actual >= value
    return actual <= value


def activity_passes(triggers, row):
    """True iff every condition in `triggers` holds for the administration
    `row`. An activity with no trigger never fires."""
    if not triggers:
        return False

    # 1. Drought-class gate: administration category must meet the minimum.
    dclass = triggers.get("dclass") or {}
    cls = dclass.get("class")
    if cls is not None:
        cat = row.get("category")
        # DroughtCategory.none (-9999) fails cat < cls automatically.
        if cat is None or cat < cls:
            return False

    # 2. Vulnerability gate (IPC phase 1..5)
    vuln = triggers.get("vuln")
    if vuln and not _condition_pass(
        row.get("ipc_phase"), vuln["op"], vuln["value"], "ipc_phase"
    ):
        return False

    # 3. Risk gate (overall computed risk score or class threshold)
    risk = triggers.get("risk")
    if risk:
        if "class" in risk:
            target_class = risk["class"]
            actual_class = row.get("risk_class")
            target_rank = _RISK_CLASS_RANK.get(target_class, 99)
            actual_rank = _RISK_CLASS_RANK.get(actual_class, -1)
            if actual_rank < target_rank:
                return False
        elif "op" in risk and "value" in risk:
            if not _condition_pass(
                row.get("risk_score"), risk["op"], risk["value"], "risk_score"
            ):
                return False

    # 4. Exposure gates — all AND-ed; unknown indicator fails safe.
    for cond in triggers.get("exp") or []:
        indicator = cond["indicator"]
        if indicator not in EXPOSURE_INDICATORS:
            return False

        # Support both 'cropland' / 'water' (authored vocab)
        # and direct column names
        actual_val = row.get(indicator)
        if actual_val is None:
            if indicator == "cropland":
                actual_val = row.get("rainfed_cropland")
            elif indicator == "water":
                actual_val = row.get("water_demand")

        if not _condition_pass(
            actual_val, cond["op"], cond["value"], indicator
        ):
            return False

    return True


# =========================================================================
# Dataset seam
# =========================================================================


def _latest_published_categories():
    """{administration_id: category} from the latest published
    publication, or {} when nothing is published yet."""
    pub = (
        Publication.objects.filter(
            status=PublicationStatus.published,
            published_at__isnull=False,
        )
        .order_by("-year_month", "-id")
        .first()
    )
    if not pub:
        return {}
    if pub.validated_values is not None:
        values = pub.validated_values
    else:
        values = pub.initial_values or []
    return {v["administration_id"]: v.get("category") for v in values}


def _min_max_norm(values: list[float | int | None]) -> list[float | None]:
    valid_nums = [v for v in values if v is not None]
    if not valid_nums:
        return [None] * len(values)
    min_v, max_v = float(min(valid_nums)), float(max(valid_nums))
    range_v = max_v - min_v
    res = []
    for v in values:
        if v is None:
            res.append(None)
        elif range_v == 0:
            res.append(0.0)
        else:
            res.append((float(v) - min_v) / range_v)
    return res


def _apply_band(score: float) -> str:
    for threshold, band in RISK_BANDS:
        if score >= threshold:
            return band
    return "Low"


def build_dataset():
    """Per-administration evaluation rows keyed by administration id.
    Reads directly from the Indicator database model and latest Publication."""
    categories = _latest_published_categories()
    indicators = list(
        Indicator.objects.select_related("administration")
        .all()
        .order_by("administration_id")
    )
    indicator_by_adm = {ind.administration_id: ind for ind in indicators}

    # Cross-row min-max norm for exposure calculation
    normed_by_subind = {}
    for subind in EXPOSURE_SUBINDICATORS:
        raw_vals = [getattr(ind, subind, None) for ind in indicators]
        normed_by_subind[subind] = _min_max_norm(raw_vals)

    dataset = {}
    for idx, adm in enumerate(Administration.objects.all()):
        ind = indicator_by_adm.get(adm.id)
        cat = categories.get(adm.id)

        if ind:
            pop = ind.population
            crop = ind.rainfed_cropland
            cat_val = ind.cattle
            wat = ind.water_demand
            ipc = ind.ipc_phase
            dvi = ind.land_use_dvi_agri

            # Exposure calculation
            valid_norms = [
                normed_by_subind[subind][idx]
                for subind in EXPOSURE_SUBINDICATORS
                if normed_by_subind[subind][idx] is not None
            ]
            exposure = (
                sum(valid_norms) / len(valid_norms) if valid_norms else 0.0
            )

            # Hazard & Vulnerability
            h_key = _DROUGHT_CATEGORY_TO_HAZARD_KEY.get(cat, "None")
            hazard = HAZARD_RESCALE.get(h_key, 0.0)
            vuln = IPC_RESCALE.get(ipc, 0.0) if ipc else 0.0

            risk_score = hazard * exposure * vuln
            risk_class = _apply_band(risk_score)
        else:
            pop = crop = cat_val = wat = ipc = dvi = None
            risk_score = 0.0
            risk_class = "Low"

        dataset[adm.id] = {
            "category": cat,
            "population": pop,
            "cropland": crop,
            "rainfed_cropland": crop,
            "cattle": cat_val,
            "water": wat,
            "water_demand": wat,
            "ipc_phase": ipc,
            "land_use_dvi_agri": dvi,
            "risk_score": risk_score,
            "risk_class": risk_class,
            "months_active": None,
        }

    return dataset
