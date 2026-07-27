from __future__ import annotations

from api.v1.v1_publication.models import Publication, PublicationStatus
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.constants import (
    HAZARD_RESCALE,
    IPC_RESCALE,
    RISK_BANDS,
    EXPOSURE_SUBINDICATORS,
)

# Mapping DroughtCategory int constants to HAZARD_RESCALE string keys
_DROUGHT_CATEGORY_TO_HAZARD_KEY = {
    DroughtCategory.none: "None",
    DroughtCategory.d0: "D0",
    DroughtCategory.d1: "D1",
    DroughtCategory.d2: "D2",
    DroughtCategory.d3: "D3",
    DroughtCategory.d4: "D4",
}


def _latest_hazard_map() -> dict[int, str]:
    """
    Fetch latest published publication and return
    {administration_id: hazard_key}.
    """
    pub = (
        Publication.objects.filter(status=PublicationStatus.published)
        .order_by("-year_month", "-id")
        .first()
    )
    if not pub:
        return {}

    values = (
        pub.validated_values
        if pub.validated_values is not None
        else (pub.initial_values or [])
    )
    res = {}
    for item in values:
        adm_id = item.get("administration_id")
        if adm_id is None:
            continue
        cat = item.get("category")
        hazard_key = _DROUGHT_CATEGORY_TO_HAZARD_KEY.get(cat, "None")
        res[adm_id] = hazard_key
    return res


def _apply_band(score: float) -> str:
    """Classify risk_score [0,1] into risk band string."""
    for threshold, band in RISK_BANDS:
        if score >= threshold:
            return band
    return "Low"


def _min_max_norm(values: list[float | int | None]) -> list[float | None]:
    """
    Min-max normalisation across a list of numeric values (None stays None).
    """
    valid_nums = [v for v in values if v is not None]
    if not valid_nums:
        return [None] * len(values)

    min_v = float(min(valid_nums))
    max_v = float(max(valid_nums))
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


def score_all(cycle: str = "latest") -> list[dict]:
    """
    Compute Hazard x Exposure x Vulnerability for all 59 Tinkhundla.
    Normalisation is min-max across the returned set per request.
    Reproduces DIH Risk Dataset Handover Risk_expected columns J & K.
    """
    indicators = list(
        Indicator.objects.select_related("administration")
        .all()
        .order_by("administration_id")
    )
    hazard_map = _latest_hazard_map()
    has_publication = bool(hazard_map)

    # Collect raw exposure values for cross-row min-max normalisation
    normed_by_subind = {}
    for subind in EXPOSURE_SUBINDICATORS:
        raw_vals = [getattr(ind, subind, None) for ind in indicators]
        normed_by_subind[subind] = _min_max_norm(raw_vals)

    results = []
    for idx, ind in enumerate(indicators):
        adm = ind.administration
        adm_id = adm.id

        # 1. Hazard component
        h_key = hazard_map.get(adm_id)
        hazard = HAZARD_RESCALE.get(h_key, 0.0) if h_key else 0.0

        # 2. Vulnerability component
        vulnerability = (
            IPC_RESCALE.get(ind.ipc_phase, 0.0)
            if ind.ipc_phase is not None
            else 0.0
        )

        # 3. Exposure component (arithmetic mean of non-null
        # normalised sub-indicators)
        sub_norms = {}
        valid_norms = []
        unavailable_subinds = []

        for subind in EXPOSURE_SUBINDICATORS:
            norm_val = normed_by_subind[subind][idx]
            sub_norm_key = f"{subind}_norm"
            if subind == "land_use_dvi_agri":
                sub_norm_key = "land_use_norm"

            sub_norms[sub_norm_key] = norm_val

            if norm_val is not None:
                valid_norms.append(norm_val)
            else:
                unavailable_subinds.append(subind)

        exposure = sum(valid_norms) / len(valid_norms) if valid_norms else 0.0

        # 4. Multiplicative Risk Score & Class
        risk_score = hazard * exposure * vulnerability
        risk_class = _apply_band(risk_score)

        # 5. Unavailable flags
        unavailable = list(unavailable_subinds)
        if not has_publication or h_key is None:
            if "hazard" not in unavailable:
                unavailable.append("hazard")
        if ind.ipc_phase is None:
            if "ipc_phase" not in unavailable:
                unavailable.append("ipc_phase")

        cycle_label = cycle if cycle != "latest" else "latest"

        results.append(
            {
                "administration": adm_id,
                "administration_name": adm.name,
                "region": adm.region,
                "hazard": round(hazard, 4),
                "exposure": round(exposure, 4),
                "vulnerability": round(vulnerability, 4),
                "risk_score": round(risk_score, 4),
                "risk_class": risk_class,
                "components": sub_norms,
                "unavailable": unavailable,
                "cycle": cycle_label,
            }
        )

    return results


def score_one(administration_id: int, cycle: str = "latest") -> dict | None:
    """Scored risk for a single administration."""
    all_scores = score_all(cycle=cycle)
    for item in all_scores:
        if item["administration"] == administration_id:
            return item
    return None
