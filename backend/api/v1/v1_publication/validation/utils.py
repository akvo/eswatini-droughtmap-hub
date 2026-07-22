"""Track 2: admin validation queue — aggregation over the review core.

Everything here derives from ``review.utils.build_rows``: the validation queue
and the reviewer queue are two screens over ONE dataset, so a change to what
"reviewed" means moves both together (design D-1).

Two counts look alike and are not:

- ``reviewers_required`` / ``reviews_completed`` count **distinct Technical
  Working Groups**, not people. Five reviewers from MoAg cover one TWG (D-2).
- ``dclass_spread`` counts **submissions**, so it can be longer than
  ``reviews_completed``. Each person gets a vote; their institution gets one
  coverage slot.
"""
from statistics import median

from api.v1.v1_publication.constants import (
    CONSENSUS_MAX_DEV,
    DISAGREEMENT_THRESHOLD,
    ValidationStatus,
    is_validated,
)
from api.v1.v1_publication.review.utils import build_rows


def scale_categories(submissions):
    """Submitted categories that sit on the ordinal scale.

    Drops ``None`` and No Data: one -9999 would drag the median off the scale
    and pin consensus to 0 for every row it touched (D-8).
    """
    return [
        s["category"]
        for s in submissions
        if is_validated(s.get("category"))
    ]


def consensus(categories):
    """Percentage agreement, weighted by how far apart the D-classes are.

    Mean absolute deviation from the median, normalized against the worst
    case — so ``[1, 2]`` (adjacent) scores 80 while ``[1, 5]`` (Normal vs D4)
    scores 20, which a modal share cannot tell apart. Outlier-robust:
    ``[1, 1, 1, 1, 5]`` is 68, not the 20 a range-based measure would give
    four agreeing reviewers.

    ``None`` when nothing usable was submitted — the bar renders empty rather
    than fabricating 0%.
    """
    if not categories:
        return None
    mid = median(categories)
    dev = sum(abs(c - mid) for c in categories) / len(categories)
    return round(100 * (1 - dev / CONSENSUS_MAX_DEV))


def reviewers_required(publication):
    """Distinct TWGs among this publication's assigned reviewers.

    The AC's "at least 5 reviewers" is the five-member TWG list, not a magic
    number: five institutional perspectives, not five headcount. Reviewers
    with no TWG are excluded from both sides of the comparison (D-2).
    """
    return (
        publication.reviews
        .exclude(user__technical_working_group=None)
        .values_list("user__technical_working_group", flat=True)
        .distinct()
        .count()
    )


def row_status(validated_category, covered, required):
    """Precedence: a decided Inkhundla is never shown as outstanding work.

    But No Data is not a decision — such a row falls through and stays in the
    actionable queue, because the admin still owes it a real class before the
    publication can go out (D-10, D-11).
    """
    if is_validated(validated_category):
        return ValidationStatus.validated
    if required > 0 and covered >= required:
        return ValidationStatus.ready
    return ValidationStatus.awaiting


def build_validation_rows(publication):
    """One validation-queue row per Inkhundla, from the shared review core."""
    required = reviewers_required(publication)
    rows = []
    for row in build_rows(publication):
        submissions = row.get("submissions") or []
        categories = scale_categories(submissions)
        covered = len({s["group"] for s in submissions if s["group"]})
        status = row_status(row["assigned_score"], covered, required)

        confidence = row.get("confidence") or {}
        rows.append({
            "administration_id": row["administration_id"],
            "label": row["name"],
            "group": row["region"],
            "zone": row["zone"],
            # Mock until a real formula exists (review queue D-6); flat so the
            # decision page can render it without unwrapping an object.
            "confidence": confidence.get("value"),
            "confidence_band": confidence.get("band"),
            "reviews_completed": covered,
            "reviews_total": required,
            "reviewers": [
                {
                    "id": s["user_id"],
                    "label": s["label"],
                    "group": s["group"],
                }
                for s in submissions
            ],
            "dclass_spread": categories,
            "consensus": consensus(categories),
            "status": status,
            "awaiting_count": (
                max(required - covered, 0)
                if status == ValidationStatus.awaiting else 0
            ),
            "validated_category": (
                row["assigned_score"]
                if is_validated(row["assigned_score"]) else None
            ),
        })
    return rows


def filter_validation_rows(rows, search=None, status=None):
    """Search by Administration name, filter by row status."""
    def keep(row):
        if search and search.lower() not in (row["label"] or "").lower():
            return False
        if status and row["status"] != status:
            return False
        return True

    return [row for row in rows if keep(row)]


def ordered_rows(publication, search=None, status=None):
    """THE queue: build, filter, order by Administration name.

    Single owner of "what the queue is, and in what order". The paginated
    table endpoint hands this to Pagination; the decision page indexes into it
    for prev/next. If the two ever computed it separately, "Next" would walk
    an order the table does not show — a bug that presents as a UI glitch and
    is actually two diverging queries (D-7).
    """
    rows = filter_validation_rows(
        build_validation_rows(publication), search=search, status=status
    )
    return sorted(rows, key=lambda r: (r["label"] or "").lower())


def build_validation_stats(rows):
    """The four summary cards.

    ready + awaiting + validated == total, so each card equals the row count
    behind its matching tab. `disagreement` cross-cuts all three and is
    deliberately not part of that sum (D-10).
    """
    counts = {status: 0 for status in ValidationStatus.FieldStr}
    disagreement = 0
    for row in rows:
        counts[row["status"]] += 1
        # Derived from the serialized spread rather than a private field, so
        # nothing internal has to survive as far as the response.
        if len(set(row["dclass_spread"])) > DISAGREEMENT_THRESHOLD:
            disagreement += 1

    def card(key, meta):
        return {
            "key": key,
            "label": ValidationStatus.FieldStr[key],
            "value": counts[key],
            "meta": meta,
        }

    return [
        card(
            ValidationStatus.ready,
            "Reviewed by every Technical Working Group",
        ),
        {
            "key": "disagreement",
            "label": "High disagreement",
            "value": disagreement,
            "meta": (
                f"More than {DISAGREEMENT_THRESHOLD} distinct D-classes"
            ),
        },
        card(ValidationStatus.validated, "Published to drought map"),
        card(ValidationStatus.awaiting, "Cannot be validated yet"),
    ]
