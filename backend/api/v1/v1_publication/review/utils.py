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


def initials(name):
    """'Ayanda Ropa' -> 'AR'. Avatar label for the validation queue."""
    parts = [p for p in (name or "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


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


def _my_suggestions(publication, user):
    """The requesting reviewer's own suggestion, keyed by administration."""
    if user is None or not user.is_authenticated:
        return {}
    review = publication.reviews.filter(user_id=user.id).first()
    if not review:
        return {}
    return {
        s["administration_id"]: s
        for s in (review.suggestion_values or [])
        if s.get("administration_id") is not None
    }


def build_rows(publication, user=None):
    """One dict per Inkhundla in ``initial_values`` (shared core).

    ``user`` is the requesting reviewer: their own suggestion rides on the row
    as ``my_suggestion``, so the queue can show what *they* approved or
    suggested — not the same thing as the validated ``assigned_score``.
    """
    initial = _category_map(publication.initial_values)
    validated = _category_map(publication.validated_values)
    total_reviewers = publication.reviews.count()
    admins = Administration.objects.in_bulk(list(initial.keys()))
    mine = _my_suggestions(publication, user)

    # Submissions per administration, across every review — including reviews
    # still in progress. A reviewer marks Tinkhundla one by one and only
    # submits the review once all of them are done, so waiting for is_completed
    # would leave the queue showing "not started" for work already done.
    #
    # Who submitted what is kept, not just the category: the validation queue
    # shows the reviewer mix and the D-class spread. It must NOT reach the
    # reviewer-facing endpoints — see _public_row in review/view.py.
    submissions = {}
    for review in publication.reviews.select_related("user").all():
        for s in (review.suggestion_values or []):
            if s.get("reviewed"):
                submissions.setdefault(s["administration_id"], []).append({
                    "user_id": review.user_id,
                    "label": initials(review.user.name),
                    "group": review.user.technical_working_group,
                    "category": s.get("category"),
                })

    rows = []
    for administration_id, cdi_class in initial.items():
        row_submissions = submissions.get(administration_id, [])
        categories = [s["category"] for s in row_submissions]
        reviewed_count = len(categories)
        status = _review_status(reviewed_count, total_reviewers)
        admin = admins.get(administration_id)
        my_suggestion = mine.get(administration_id)
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
            "my_suggestion": {
                "category": my_suggestion.get("category"),
                "reviewed": bool(my_suggestion.get("reviewed")),
                "comment": my_suggestion.get("comment") or "",
            } if my_suggestion else None,
            "assigned_score": validated.get(administration_id),
            "review_status": status,
            "disputed": (
                len({c for c in categories if c is not None}) > 1
            ),
            # Admin-only (validation queue). Stripped from every /reviewer/*
            # response by _public_row — see review/view.py.
            "submissions": row_submissions,
        })
    return rows


def public_row(row):
    """Drop admin-only fields before a row reaches a reviewer.

    ``submissions`` (added by build_rows) carries every colleague's D-class.
    The review queue deliberately shows a reviewer only their own
    ``my_suggestion``: seeing what four others chose before submitting turns
    five independent judgements into one plus four echoes, which is what the
    TWG-coverage threshold exists to prevent.

    Lives here, next to build_rows, so the field's whole lifecycle — added in
    one function, stripped in the next — reads in one place. Applied at all
    three /reviewer/* response sites; there is no single chokepoint, because
    the detail endpoint does not go through the filtered-rows helper.
    """
    return {k: v for k, v in row.items() if k != "submissions"}


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


def is_mine_reviewed(row):
    """The requesting reviewer has already reviewed this Inkhundla."""
    return bool((row.get("my_suggestion") or {}).get("reviewed"))


def _tally(rows):
    """Raw counters behind the summary — for this month and the previous."""
    counts = {"fully_reviewed": 0, "partially_reviewed": 0, "not_started": 0}
    tally = {
        "total": len(rows),
        "disputed": 0,
        "high_confidence": 0,
        "validated": 0,
    }
    for row in rows:
        counts[row["review_status"]] += 1
        if row["disputed"]:
            tally["disputed"] += 1
        # "ready to bulk-accept" — high confidence AND not yet reviewed by the
        # requesting reviewer, so the count (and the banner) drop to zero once
        # they have been accepted.
        if row["confidence"]["band"] == "high" and not is_mine_reviewed(row):
            tally["high_confidence"] += 1
        if row["assigned_score"] is not None:
            tally["validated"] += 1
    tally.update(counts)
    tally["reviews_collected"] = (
        counts["fully_reviewed"] + counts["partially_reviewed"]
    )
    return tally


def _pct(value, total):
    return round(value / total * 100) if total else 0


def _delta(current, previous):
    """Change vs the previous publication. ``None`` when there is no previous
    publication to compare against — the card then renders no arrow."""
    if previous is None:
        return None
    change = current - previous
    direction = "flat"
    if change > 0:
        direction = "up"
    elif change < 0:
        direction = "down"
    return {"value": change, "direction": direction}


def build_stats(rows, previous_rows=None):
    """Cards + half-doughnut summary derived from ``build_rows`` output.

    ``previous_rows`` are the rows of the preceding publication month; when
    given, every card carries a ``delta`` against it (percentage points for
    ``tinkhundla_reviewed``, absolute counts elsewhere).
    """
    now = _tally(rows)
    was = _tally(previous_rows) if previous_rows is not None else None

    def delta(key):
        return _delta(now[key], was[key] if was else None)

    return {
        "pending_review": {
            "value": now["disputed"],
            "label": "disagreement detected / sign-off needed",
            "delta": delta("disputed"),
        },
        "high_confidence": {
            "value": now["high_confidence"],
            "label": "ready to bulk-accept",
            "is_mock": True,
            "delta": delta("high_confidence"),
        },
        "tinkhundla_reviewed": {
            "value": now["validated"],
            "total": now["total"],
            "delta": _delta(
                _pct(now["validated"], now["total"]),
                _pct(was["validated"], was["total"]) if was else None,
            ),
        },
        "overall_readiness": _pct(now["reviews_collected"], now["total"]),
        "reviews_collected": {
            "value": now["reviews_collected"],
            "total": now["total"],
        },
        "status_breakdown": [
            {
                "key": "fully_reviewed",
                "label": "Fully reviewed",
                "value": now["fully_reviewed"],
                "note": "ready to validate",
                "delta": delta("fully_reviewed"),
            },
            {
                "key": "partially_reviewed",
                "label": "Partially reviewed",
                "value": now["partially_reviewed"],
                "note": "in progress",
                "delta": delta("partially_reviewed"),
            },
            {
                "key": "not_started",
                "label": "Not started",
                "value": now["not_started"],
                "note": "awaiting first review",
                "delta": delta("not_started"),
            },
        ],
    }
