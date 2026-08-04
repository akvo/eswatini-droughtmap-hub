from __future__ import annotations

from api.v1.v1_indicators.constants import (
    EXPOSURE_NORM_KEYS,
    EXPOSURE_SUBINDICATORS,
)
from api.v1.v1_indicators.services import score_all
from api.v1.v1_publication.models import Publication, PublicationStatus
from api.v1.v1_risk_level.constants import (
    BAND_MAP,
    DCLASS_BY_CATEGORY,
    ELIGIBILITY_EXPOSURE_FIELDS,
    EXPOSURE_UNITS,
    NO_CONFIDENCE_REASON,
    NO_WATER_POINTS_REASON,
    WATER_DEMAND_UNIT_STATUS,
)
from api.v1.v1_risk_level.utils import band_thresholds, drought_trend


def _dclass(category: int | None) -> str | None:
    """Validated DroughtCategory → D-class label, or None when the cycle
    carries no decision for this Inkhundla.

    Reads the category, never the rescaled hazard: `normal` and `none` are
    both hazard 0.0, so labelling from the float published wet conditions as
    "No Data" on the public page.
    """
    return DCLASS_BY_CATEGORY.get(category)


def _latest_publication():
    return (
        Publication.objects.filter(
            status=PublicationStatus.published, published_at__isnull=False
        )
        .order_by("-year_month", "-id")
        .first()
    )


def _publication_meta(publication) -> dict | None:
    if publication is None:
        return None
    return {
        "id": publication.id,
        "year_month": (
            publication.year_month.strftime("%Y-%m")
            if hasattr(publication.year_month, "strftime")
            else str(publication.year_month)
        ),
        "published_at": (
            publication.published_at.isoformat()
            if hasattr(publication.published_at, "isoformat")
            else str(publication.published_at)
        ),
    }


def _ranked_rows(scored: list) -> list:
    """Scored rows ranked by risk_score desc, name asc (deterministic
    tie-break). Administrations with no score are excluded — they cannot be
    ranked against the rest."""
    rows = []
    for r in scored:
        if r.get("risk_score") is None or r.get("risk_class") is None:
            continue

        rows.append(
            {
                "administration_id": r["administration"],
                "name": r["administration_name"],
                "region": r["region"],
                "risk_score": r["risk_score"],
                "risk_class": r["risk_class"],
                "band": BAND_MAP.get(r["risk_class"], "monitor"),
                "components": {
                    "hazard": r["hazard"],
                    "d_class": _dclass(r.get("category")),
                    "exposure": r["exposure"],
                    "vulnerability": r["vulnerability"],
                    **r.get("components", {}),
                    "unavailable": r.get("unavailable", []),
                },
            }
        )

    rows.sort(key=lambda x: (-x["risk_score"], x["name"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def compute_risk_level_list(
    region: str | None = None, band: str | None = None
) -> dict:
    """
    Public ranked risk level list.
    Wraps v1_indicators.services.score_all() — no formula re-implementation.
    Stateless: re-computed on every request (59 administrations, trivial CPU).
    """
    pub = _latest_publication()
    if pub is None:
        return {"publication": None, "count": 0, "data": []}

    rows = _ranked_rows(score_all())

    # Apply query-param filters AFTER rank assignment
    if region:
        rows = [r for r in rows if r["region"] == region]
    if band:
        rows = [r for r in rows if r["band"] == band]

    return {
        "publication": _publication_meta(pub),
        "count": len(rows),
        "data": rows,
    }


def _exposure_row(indicator, field: str, components: dict) -> dict:
    """One exposure accordion row: the raw absolute plus, for the four scored
    sub-indicators, the normalised value it contributed. Eligibility counts
    carry scored=False so the UI cannot present them as score inputs."""
    row = {
        "key": field,
        "value": getattr(indicator, field, None) if indicator else None,
        "unit": EXPOSURE_UNITS.get(field),
        "norm": components.get(EXPOSURE_NORM_KEYS.get(field)),
        "scored": field in EXPOSURE_SUBINDICATORS,
    }
    if field == "water_demand":
        row["meta"] = {"unit_status": WATER_DEMAND_UNIT_STATUS}
    return row


def _people_per_water_point(indicator) -> dict:
    """Water access pressure — CONTEXT only (RL-2 D-5). Never a vulnerability
    input: V is the IPC layer alone."""
    row = {
        "key": "people_per_water_point",
        "value": None,
        "unit": "people/point",
        "scored": False,
        "meta": {"basis": "population / (boreholes + taps)"},
    }
    if indicator is None:
        row["meta"]["reason"] = NO_WATER_POINTS_REASON
        return row

    points = (indicator.boreholes or 0) + (indicator.taps or 0)
    row["meta"]["boreholes"] = indicator.boreholes
    row["meta"]["taps"] = indicator.taps
    # Zero water points is not zero pressure — it is unknown, and dividing
    # would raise. Both gaps report the reason instead of a number.
    if not points or indicator.population is None:
        row["meta"]["reason"] = NO_WATER_POINTS_REASON
        return row

    row["value"] = round(indicator.population / points)
    return row


def _vulnerability_rows(indicator) -> list:
    """IPC is the only scored row (redesign D-7); water access rides along as
    labelled context (RL-2 D-5)."""
    rows = []
    if indicator is not None and indicator.ipc_phase is not None:
        rows.append(
            {
                "key": "ipc_phase",
                "value": indicator.ipc_phase,
                "format": "ipc",
                "scored": True,
            }
        )
    rows.append(_people_per_water_point(indicator))
    return rows


def compute_risk_level_detail(administration) -> dict:
    """Full score build-up for one Inkhundla (RL-2).

    Composes — never recomputes — the v1_indicators score with the publication
    cycle, this Inkhundla's rank in the public list, the raw absolutes behind
    each normalised exposure component, and the drought trend.
    """
    pub = _latest_publication()
    scored = score_all()
    raw = next(
        (s for s in scored if s["administration"] == administration.pk), {}
    )
    ranked = next(
        (
            r
            for r in _ranked_rows(scored)
            if r["administration_id"] == administration.pk
        ),
        None,
    )
    indicator = getattr(administration, "indicator", None)
    components = raw.get("components", {})
    hazard = raw.get("hazard")
    risk_score = raw.get("risk_score")
    publication = _publication_meta(pub)

    return {
        "period": publication["year_month"] if publication else None,
        "publication": publication,
        "administration": {
            "id": administration.pk,
            "name": administration.name,
            "region": administration.region,
            "zone": administration.zone,
        },
        "rank": ranked["rank"] if ranked else None,
        "drought": {
            "key": _dclass(raw.get("category")),
            "value": hazard,
            # Real confidence needs a station baseline the hub does not have
            # (RL-2 D-7) — null with a reason, never a mock on a public page.
            "confidence": {
                "band": None,
                "value": None,
                "meta": {"reason": NO_CONFIDENCE_REASON},
            },
            **drought_trend(administration.pk),
        },
        "exposure": {
            "value": raw.get("exposure"),
            "data": [
                _exposure_row(indicator, field, components)
                for field in (
                    EXPOSURE_SUBINDICATORS + ELIGIBILITY_EXPOSURE_FIELDS
                )
            ],
            "unavailable": raw.get("unavailable", []),
        },
        "vulnerability": {
            "value": raw.get("vulnerability"),
            "data": _vulnerability_rows(indicator),
        },
        "risk_score": {
            "value": risk_score,
            "class": raw.get("risk_class"),
            "meta": {
                "band": (
                    BAND_MAP.get(raw.get("risk_class"))
                    if risk_score is not None
                    else None
                ),
                "scale": [0, 1],
                "band_thresholds": band_thresholds(),
            },
        },
        "source": {
            "name": indicator.source if indicator else None,
            "as_of": (
                indicator.as_of.isoformat()
                if indicator and indicator.as_of
                else None
            ),
            "is_placeholder": (
                indicator.is_placeholder if indicator else None
            ),
        },
    }
