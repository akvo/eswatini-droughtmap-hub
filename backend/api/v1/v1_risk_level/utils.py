"""Derivations behind the Risk Level payloads.

Kept out of ``service.py`` so the pieces stay reusable: the SOP "consecutive
number of months" trigger gate (redesign A-6) needs the same publication
history scan, and the band floors are published by both endpoints.
"""
from api.v1.v1_indicators.constants import RISK_BANDS
from api.v1.v1_publication.constants import DroughtCategory, PublicationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_risk_level.constants import (
    BAND_MAP,
    RECOVERING,
    STABLE,
    TREND_DESC,
    TREND_HISTORY_LIMIT,
    WORSENING,
)


def band_thresholds() -> dict:
    """Lowest score at which each action band starts, on the 0-1 scale.

    Derived from RISK_BANDS x BAND_MAP so the published thresholds can never
    drift from the classification the service actually applies (RL-2 D-3).
    RISK_BANDS is ordered descending, so the last write per band is its floor.
    """
    thresholds = {}
    for threshold, risk_class in RISK_BANDS:
        thresholds[BAND_MAP.get(risk_class, "monitor")] = threshold
    return thresholds


def published_history(limit: int = TREND_HISTORY_LIMIT) -> list:
    """Published publications, newest first."""
    return list(
        Publication.objects.filter(
            status=PublicationStatus.published, published_at__isnull=False
        ).order_by("-year_month", "-id")[:limit]
    )


def _category(publication, administration_id: int):
    """This Inkhundla's D-class in one cycle, or None when it has no real
    class there. ``none`` (-9999) is raster no-signal, not a decision — it
    must not be compared as if it were the mildest class."""
    values = (
        publication.validated_values
        if publication.validated_values is not None
        else (publication.initial_values or [])
    )
    for item in values or []:
        if item.get("administration_id") == administration_id:
            category = item.get("category")
            if category is None or category == DroughtCategory.none:
                return None
            return category
    return None


def _direction(newer: int, older: int) -> str:
    if newer > older:
        return WORSENING
    if newer < older:
        return RECOVERING
    return STABLE


def drought_trend(administration_id: int, publications=None) -> dict:
    """``{"trend", "trend_desc"}`` for the latest published cycle.

    ``trend`` is the direction of the most recent cycle-to-cycle step;
    ``trend_desc`` counts how many consecutive steps ran that way. Both are
    None until two consecutive cycles carry a real class for this Inkhundla.
    """
    history = (
        published_history() if publications is None else list(publications)
    )

    categories = []
    for publication in history:
        category = _category(publication, administration_id)
        # Stop at the first gap: comparing across a missing cycle would
        # report a step that never happened.
        if category is None:
            break
        categories.append(category)

    if len(categories) < 2:
        return {"trend": None, "trend_desc": None}

    trend = _direction(categories[0], categories[1])

    months = 0
    for newer, older in zip(categories, categories[1:]):
        if _direction(newer, older) != trend:
            break
        months += 1

    plural = "" if months == 1 else "s"
    return {
        "trend": trend,
        "trend_desc": f"{months} month{plural} {TREND_DESC[trend]}",
    }
