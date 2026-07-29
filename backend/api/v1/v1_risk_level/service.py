from __future__ import annotations

from api.v1.v1_indicators.services import score_all
from api.v1.v1_publication.models import Publication, PublicationStatus
from api.v1.v1_risk_level.constants import BAND_MAP


def _hazard_to_dclass(hazard: float | None) -> str:
    """Reverse HAZARD_RESCALE float → D-class label."""
    if hazard is None:
        return "None"
    mapping = {
        0.0: "None",
        0.2: "D0",
        0.4: "D1",
        0.6: "D2",
        0.8: "D3",
        1.0: "D4",
    }
    return mapping.get(round(hazard, 1), "None")


def compute_risk_level_list(
    region: str | None = None, band: str | None = None
) -> dict:
    """
    Public ranked risk level list.
    Wraps v1_indicators.services.score_all() — no formula re-implementation.
    Stateless: re-computed on every request (59 administrations, trivial CPU).
    """
    pub = (
        Publication.objects.filter(
            status=PublicationStatus.published, published_at__isnull=False
        )
        .order_by("-year_month", "-id")
        .first()
    )
    if pub is None:
        return {"publication": None, "count": 0, "data": []}

    scored = score_all()

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
                    "d_class": _hazard_to_dclass(r["hazard"]),
                    "exposure": r["exposure"],
                    "vulnerability": r["vulnerability"],
                    **r.get("components", {}),
                    "unavailable": r.get("unavailable", []),
                },
            }
        )

    # Sort: risk_score desc, name asc (deterministic tie-break)
    rows.sort(key=lambda x: (-x["risk_score"], x["name"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # Apply query-param filters AFTER rank assignment
    if region:
        rows = [r for r in rows if r["region"] == region]
    if band:
        rows = [r for r in rows if r["band"] == band]

    return {
        "publication": {
            "id": pub.id,
            "year_month": (
                pub.year_month.strftime("%Y-%m")
                if hasattr(pub.year_month, "strftime")
                else str(pub.year_month)
            ),
            "published_at": (
                pub.published_at.isoformat()
                if hasattr(pub.published_at, "isoformat")
                else str(pub.published_at)
            ),
        },
        "count": len(rows),
        "data": rows,
    }
