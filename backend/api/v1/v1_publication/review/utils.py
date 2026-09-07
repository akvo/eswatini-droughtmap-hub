"""Aggregation core for the "This month review queue" screens (Figma 3117).

`build_rows` computes the per-Inkhundla dataset once; the stats, table and map
endpoints all slice it. Every field is real aggregation: over Publication +
Review for the review progress, and over the satellite × station comparison in
``v1_weather.confidence`` for the confidence score and the stations-vs-satellite
deltas. A score of 0 means an input was missing for that Inkhundla, with
``meta.reason`` naming which — never a placeholder standing in for one.
"""
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    Review,
)
from api.v1.v1_publication.constants import (
    DroughtCategory,
)
from api.v1.v1_weather.confidence import (
    not_computable,
    publication_confidence,
)
from api.v1.v1_weather.constants import (
    CONFIDENCE_NO_SATELLITE_SPI,
    CONFIDENCE_NO_SATELLITE_TEMPERATURE,
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


def _value_map(values):
    """administration_id -> raw CDI-E value (initial_values carries both a
    ``category`` and the composite ``value``; the queue only needs category,
    the individual page also needs the score)."""
    return {
        v["administration_id"]: v.get("value")
        for v in (values or [])
    }


def recent_publications(anchor, limit=12):
    """The anchor publication plus its ``limit-1`` predecessors by month
    (newest first). Anchors the 12-month CDI-E history + decision history to
    the publication being reviewed, not to "now"."""
    return list(
        Publication.objects.filter(year_month__lte=anchor.year_month)
        .order_by("-year_month")[:limit]
    )


def indicator_values(publication, administration_id):
    """Raw percentile ranks for each attached indicator raster, this admin.
    Labels/colours are frontend config (WX-3 D-4) — API sends key+value only.
    ``value`` is null when the raster has no entry for the Inkhundla."""
    out = []
    for raster in publication.rasters.all():
        value = next(
            (
                item.get("value")
                for item in (raster.values or [])
                if item.get("administration_id") == administration_id
            ),
            None,
        )
        out.append({"key": raster.indicator, "value": value})
    return out


def cdi_history(administration_id, publications):
    """CDI-E composite value for this admin across ``publications``,
    oldest -> newest (the chart plots the current month on the far right)."""
    history = []
    for pub in reversed(publications):
        history.append({
            "period": pub.year_month.strftime("%Y-%m"),
            "value": _value_map(pub.initial_values).get(administration_id),
        })
    return history


def reviewer_decision_history(user, administration_id, publications):
    """THIS reviewer's own submitted drought-class picks for this admin,
    newest first. AC-critical: request.user's Review only — never other
    reviewers, never the validator's ValidationDecision table."""
    if user is None or not user.is_authenticated:
        return []
    reviews = {
        r.publication_id: r
        for r in Review.objects.filter(
            publication__in=publications, user_id=user.id
        )
    }
    out = []
    for pub in publications:  # newest first
        review = reviews.get(pub.id)
        if not review:
            continue
        suggestion = next(
            (
                s for s in (review.suggestion_values or [])
                if s.get("administration_id") == administration_id
                and s.get("reviewed")
            ),
            None,
        )
        if suggestion is None:
            continue
        decided = review.completed_at or review.updated_at
        out.append({
            "period": pub.year_month.strftime("%Y-%m"),
            "category": suggestion.get("category"),
            "comment": suggestion.get("comment") or "",
            "decided_at": decided.isoformat() if decided else None,
        })
    return out


def build_administration_cdi(publication, administration_id, cdi_class,
                             publications):
    """The individual review page's CDI-E block: composite score+category,
    per-indicator percentile ranks, and the 12-month history."""
    return {
        "score": _value_map(publication.initial_values).get(
            administration_id
        ),
        "category": cdi_class,
        "indicators": indicator_values(publication, administration_id),
        "history": cdi_history(administration_id, publications),
    }


def _confidence(scores, administration_id, cdi_class):
    """This Inkhundla's satellite-vs-station agreement score, 0-5.

    An Inkhundla the CDI had no signal for is not scoreable at all — there is
    no satellite side to compare the station against — so it short-circuits
    before the framework runs.
    """
    if cdi_class is None or cdi_class == DroughtCategory.none:
        return not_computable(CONFIDENCE_NO_SATELLITE_SPI).as_dict()
    computed = scores.get(administration_id)
    if computed is None:
        return not_computable(CONFIDENCE_NO_SATELLITE_SPI).as_dict()
    return computed.as_dict()


def _stations_vs_satellite(confidence):
    """The queue's "Stations vs Satellite" column, from the same comparison.

    SPI is the real delta the confidence score was built on. LST stays null:
    the satellite side publishes no temperature in degrees C (see
    `v1_weather/confidence.py`), so there is nothing to difference.
    """
    return {
        "spi": (confidence.get("meta") or {}).get("spi", {}).get("delta"),
        "lst": None,
        "lst_reason": CONFIDENCE_NO_SATELLITE_TEMPERATURE,
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
    # Once for the whole publication, not once per Inkhundla.
    scores = publication_confidence(publication)

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
                    "name": review.user.name or "",
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
        confidence = _confidence(scores, administration_id, cdi_class)
        rows.append({
            "administration_id": administration_id,
            "name": admin.name if admin else None,
            "region": admin.region if admin else None,
            "zone": admin.zone if admin else None,
            "cdi_class": cdi_class,
            "stations_vs_satellite": _stations_vs_satellite(confidence),
            "confidence": confidence,
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
    """Apply the review-queue table / map filters over pre-built rows.

    ``reviewed`` is **scoped to the requesting reviewer** and tri-state:
    ``None`` keeps every row, ``True`` is the "Review completed" chip, ``False``
    is "Awaiting review". Both chips read the same signal — whether *this*
    reviewer has submitted a suggestion (``my_suggestion.reviewed``) — so they
    partition the queue exactly, and match the ``tinkhundla_reviewed`` /
    ``pending_review`` cards respectively.

    Two earlier readings were wrong for different reasons: ``!= not_started``
    made the chip identical to "All" as soon as one reviewer worked the queue,
    and ``== fully_reviewed`` (team N/N) showed a reviewer rows they had never
    touched while hiding ones they had. Rows carry ``my_suggestion`` only when
    ``build_rows`` is given a user, so this filter is reviewer endpoints only.
    """
    def keep(row):
        if search and search.lower() not in (row["name"] or "").lower():
            return False
        if confidence and row["confidence"]["band"] != confidence:
            return False
        if reviewed is not None and is_mine_reviewed(row) != reviewed:
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
    """Raw counters behind the summary — for this month and the previous.

    The top cards + Assessment summary (mine_reviewed, pending, readiness,
    reviews_collected) are scoped to the requesting reviewer: their own
    submissions out of the 59 Tinkhundla, never crossed with other reviewers.
    The fully/partially/not_started breakdown stays team-level — queue
    validation-readiness ("ready to validate" / "awaiting first review") — as
    the design shows.
    """
    counts = {"fully_reviewed": 0, "partially_reviewed": 0, "not_started": 0}
    tally = {
        "total": len(rows),
        "disputed": 0,
        "high_confidence": 0,
        "validated": 0,
        "mine_reviewed": 0,
        # Confidence coverage (WX-2b): how many Inkhundla carry a real band,
        # and why the rest do not.
        "scored": 0,
        "unscored_reasons": {},
    }
    for row in rows:
        counts[row["review_status"]] += 1
        confidence = row["confidence"]
        if confidence["band"]:
            tally["scored"] += 1
        else:
            # ONLY when there is no band. A scored row still carries
            # `no_satellite_temperature` — the standing note that the
            # temperature half of the framework has no source, not a failure —
            # so tallying reasons unconditionally would report a healthy
            # publication as entirely unscored.
            reason = (confidence.get("meta") or {}).get("reason") or "unknown"
            tally["unscored_reasons"][reason] = (
                tally["unscored_reasons"].get(reason, 0) + 1
            )
        if row["disputed"]:
            tally["disputed"] += 1
        # "ready to bulk-accept" — high confidence AND not yet reviewed by the
        # requesting reviewer, so the count (and the banner) drop to zero once
        # they have been accepted.
        if row["confidence"]["band"] == "high" and not is_mine_reviewed(row):
            tally["high_confidence"] += 1
        if row["assigned_score"] is not None:
            tally["validated"] += 1
        if is_mine_reviewed(row):
            tally["mine_reviewed"] += 1
    tally.update(counts)
    # The requesting reviewer's own outstanding rows: pending + reviewed == the
    # 59 Tinkhundla, and both agree with the queue header's progress_review.
    tally["pending"] = tally["total"] - tally["mine_reviewed"]
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
        # Outstanding review work — NOT the disagreement count, which the card
        # used to show while being titled "Pending review".
        "pending_review": {
            "value": now["pending"],
            "label": "awaiting review / sign-off",
            "delta": delta("pending"),
        },
        # The disagreement signal keeps its own key so it is not lost now that
        # `pending_review` means what its title says.
        "disagreements": {
            "value": now["disputed"],
            "label": "disagreement detected",
            "delta": delta("disputed"),
        },
        "high_confidence": {
            "value": now["high_confidence"],
            "label": "ready to bulk-accept",
            "delta": delta("high_confidence"),
        },
        # THIS reviewer's own progress. Previously read `validated`, i.e. the
        # NDRMA validator's output, which is empty for the whole review stage.
        "tinkhundla_reviewed": {
            "value": now["mine_reviewed"],
            "total": now["total"],
            "delta": _delta(
                _pct(now["mine_reviewed"], now["total"]),
                _pct(was["mine_reviewed"], was["total"]) if was else None,
            ),
        },
        # The requesting reviewer's own progress out of the 59 Tinkhundla
        # (Figma "Reviews collected 25/59") — not crossed with other reviewers.
        # Publication-wide, and deliberately not delta'd: this describes the
        # month's input data, not the reviewer's progress through it.
        "confidence_coverage": {
            "scored": now["scored"],
            "total": now["total"],
            # Dominant cause first; key ties broken alphabetically so the
            # order is stable between requests.
            "unscored": [
                {"key": key, "value": value}
                for key, value in sorted(
                    now["unscored_reasons"].items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        },
        "overall_readiness": _pct(now["mine_reviewed"], now["total"]),
        "reviews_collected": {
            "value": now["mine_reviewed"],
            "total": now["total"],
        },
        "status_breakdown": [
            {
                "key": "fully_reviewed",
                "label": "Fully reviewed",
                "value": now["fully_reviewed"],
                "note": "of queue | ready to validate",
                "delta": delta("fully_reviewed"),
            },
            {
                "key": "partially_reviewed",
                "label": "Partially reviewed",
                "value": now["partially_reviewed"],
                "note": "of queue | in progress",
                "delta": delta("partially_reviewed"),
            },
            {
                "key": "not_started",
                "label": "Not started",
                "value": now["not_started"],
                "note": "of queue | awaiting first review",
                "delta": delta("not_started"),
            },
        ],
    }
