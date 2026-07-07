"""Aggregation core for the "This month review queue" screens (Figma 3117).

`build_rows` computes the per-Inkhundla dataset once; the stats, table and map
endpoints all slice it. Most fields are real aggregation over Publication +
Review; the fields flagged ``is_mock`` (confidence, stations vs satellite, and
the confidence-derived ``high_confidence`` count)
are deterministic placeholders
until the Δ-based confidence formula and station data exist. See CLAUDE.md
"Frontend Mock Data" — these responses are the backend contract.
"""
from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.constants import (
    DroughtCategory,
    MOCK_STATIONS,
    BANDS,
)


def _category_map(values):
    return {
        v["administration_id"]: v.get("category")
        for v in (values or [])
    }


def _mock_confidence(administration_id, cdi_class):
    # Deterministic (no random -> reproducible tests) mock until real formula.
    if cdi_class is None or cdi_class == DroughtCategory.none:
        return {"value": None, "band": None, "is_mock": True}
    return {
        "value": round(1 + (administration_id % 900) / 100, 2),
        "band": BANDS[administration_id % 3],
        "is_mock": True,
    }


def _review_status(reviewed_count, total_reviewers):
    if reviewed_count == 0:
        return "not_started"
    if total_reviewers and reviewed_count >= total_reviewers:
        return "fully_reviewed"
    return "partially_reviewed"


def build_rows(publication):
    """One dict per Inkhundla in ``initial_values`` (shared core)."""
    initial = _category_map(publication.initial_values)
    validated = _category_map(publication.validated_values)
    total_reviewers = publication.reviews.count()
    admins = Administration.objects.in_bulk(list(initial.keys()))

    # categories submitted per administration across completed reviews
    reviewed = {}
    for review in publication.completed_reviews:
        for s in (review.suggestion_values or []):
            if s.get("reviewed"):
                reviewed.setdefault(
                    s["administration_id"], []
                ).append(s.get("category"))

    rows = []
    for administration_id, cdi_class in initial.items():
        categories = reviewed.get(administration_id, [])
        reviewed_count = len(categories)
        status = _review_status(reviewed_count, total_reviewers)
        admin = admins.get(administration_id)
        rows.append({
            "administration_id": administration_id,
            "name": admin.name if admin else None,
            "region": admin.region if admin else None,
            "zone": admin.zone if admin else None,
            "cdi_class": cdi_class,
            "stations_vs_satellite": dict(MOCK_STATIONS),
            "confidence": _mock_confidence(administration_id, cdi_class),
            "reviews": {
                "completed": reviewed_count,
                "total": total_reviewers,
            },
            "assigned_score": validated.get(administration_id),
            "review_status": status,
            "disputed": (
                len({c for c in categories if c is not None}) > 1
            ),
        })
    return rows


def filter_rows(rows, search=None, confidence=None,
                reviewed=None, region=None, zone=None):
    """Apply the review-queue table / map filters over pre-built rows."""
    def keep(row):
        if search and search.lower() not in (row["name"] or "").lower():
            return False
        if confidence and row["confidence"]["band"] != confidence:
            return False
        if reviewed and row["review_status"] == "not_started":
            return False
        if region and row["region"] != region:
            return False
        if zone and row["zone"] != zone:
            return False
        return True

    return [row for row in rows if keep(row)]


def build_stats(rows):
    """Cards + half-doughnut summary derived from ``build_rows`` output."""
    total = len(rows)
    counts = {"fully_reviewed": 0, "partially_reviewed": 0, "not_started": 0}
    disputed = 0
    high_confidence = 0
    validated_count = 0
    for row in rows:
        counts[row["review_status"]] += 1
        if row["disputed"]:
            disputed += 1
        if row["confidence"]["band"] == "high":
            high_confidence += 1
        if row["assigned_score"] is not None:
            validated_count += 1

    reviews_collected = (
        counts["fully_reviewed"] + counts["partially_reviewed"]
    )
    return {
        "pending_review": {
            "value": disputed,
            "label": "disagreement detected / sign-off needed",
        },
        "high_confidence": {
            "value": high_confidence,
            "label": "ready to bulk-accept",
            "is_mock": True,
        },
        "tinkhundla_reviewed": {
            "value": validated_count,
            "total": total,
        },
        "overall_readiness": (
            round(reviews_collected / total * 100) if total else 0
        ),
        "reviews_collected": {
            "value": reviews_collected,
            "total": total,
        },
        "status_breakdown": [
            {
                "key": "fully_reviewed",
                "label": "Fully reviewed",
                "value": counts["fully_reviewed"],
                "note": "ready to validate",
            },
            {
                "key": "partially_reviewed",
                "label": "Partially reviewed",
                "value": counts["partially_reviewed"],
                "note": "in progress",
            },
            {
                "key": "not_started",
                "label": "Not started",
                "value": counts["not_started"],
                "note": "awaiting first review",
            },
        ],
    }
