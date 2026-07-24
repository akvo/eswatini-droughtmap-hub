"""Track 2: the Validation Decision page — one Inkhundla, one final D-class.

Split from ``validation/utils.py`` (which owns the queue aggregation) to keep
each file to one concern and the import direction one-way: decision imports
utils, never the reverse.

The two rules most easily got wrong live here, so they are single functions
with their own tests:

- ``majority_of`` breaks ties toward **severity**, and says that it tied. A
  tie is not visible in the consensus score — four reviewers split 2-2 across
  adjacent classes score 80, which is genuinely tight agreement about severity
  even though there is no modal class to accept.
- ``neighbours`` locates the row in ``filtered u {current}``, so Prev/Next keep
  working after a status change drops the row out of its own tab.
"""
from collections import Counter

from django.db import transaction
from django.utils import timezone

from api.v1.v1_publication.constants import (
    BULK_REASONING_PREFIX,
    AgreementFilter,
    ConsensusBand,
    DroughtCategory,
    ValidationStatus,
    is_validated,
)
from api.v1.v1_publication.models import Administration, ValidationDecision
from api.v1.v1_publication.review.utils import initials
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.validation.utils import (
    consensus,
    ordered_rows,
    reviewers_required,
)
from utils.custom_pagination import Pagination


def consensus_band(value):
    """Band a consensus score. ``none`` when there is nothing to band."""
    if value is None:
        return ConsensusBand.none
    for floor, band in ConsensusBand.THRESHOLDS:
        if value >= floor:
            return band
    return ConsensusBand.none


def majority_of(categories):
    """``(majority, is_tie)`` over submitted D-classes.

    Ties break toward the **more severe** class: this is a drought
    early-warning system, under-calling severity has asymmetric cost, and the
    validator can always pick down. Deterministic, so the pre-selected chip
    cannot change between two reads of the same data.
    """
    if not categories:
        return None, False
    counts = Counter(categories)
    top = max(counts.values())
    tied = sorted(c for c, n in counts.items() if n == top)
    return max(tied), len(tied) > 1


def build_agreement(categories):
    """The vote tally behind the agreement bar and the pre-selected chip.

    ``total_submitted`` counts **submissions**, not TWGs, so it can exceed
    ``reviews_total``: an institution gets one coverage slot but each person
    gets a vote.
    """
    majority, is_tie = majority_of(categories)
    counts = Counter(categories)
    score = consensus(categories)
    return {
        "band": consensus_band(score),
        "majority_count": counts[majority] if majority is not None else 0,
        "total_submitted": len(categories),
        "is_tie": is_tie,
        "tied_categories": (
            sorted(c for c, n in counts.items() if n == max(counts.values()))
            if is_tie else []
        ),
        "distribution": [
            {"category": category, "count": counts[category]}
            for category in sorted(counts)
        ],
    }


def build_reviews(publication, administration_id):
    """One row per **assigned** reviewer, submitted or not (AC-4.1/4.2).

    Built from the reviewer roster rather than from ``build_rows``'
    ``submissions``, which only contains reviewers who have already submitted
    — the page has to render a pending row for those who have not.

    ``submitted_at`` is the review's own timestamp, the closest thing the data
    has: ``suggestion_values`` entries carry no per-Inkhundla time.
    """
    rows = []
    for review in publication.reviews.select_related("user").all():
        entry = next(
            (
                s for s in (review.suggestion_values or [])
                if s.get("administration_id") == administration_id
                and s.get("reviewed")
            ),
            None,
        )
        rows.append({
            "user_id": review.user_id,
            "initials": initials(review.user.name),
            "name": review.user.name,
            "organisation": review.user.technical_working_group,
            "email": review.user.email,
            "submitted_at": (
                (review.updated_at or review.created_at) if entry else None
            ),
            "category": entry.get("category") if entry else None,
            "comment": (entry.get("comment") or None) if entry else None,
            "hidden": False,
        })
    return rows


def has_submitted(reviews, user_id):
    """Has this reviewer submitted their own D-class for this Inkhundla?"""
    return any(
        r["user_id"] == user_id and r["category"] is not None for r in reviews
    )


def mask_reviews(reviews, user_id):
    """Strip colleagues' judgements, keeping the roster intact.

    Seeing what four colleagues chose before submitting turns five independent
    judgements into one plus four echoes — which is exactly what the
    five-TWG threshold exists to create. The row survives so the count still
    matches the roster; only the judgement and the identity go.

    ``organisation`` stays: which institutions were asked is not a judgement,
    and the queue already exposes it.
    """
    masked = []
    for row in reviews:
        if row["user_id"] == user_id:
            masked.append(row)
            continue
        masked.append({
            "user_id": None,
            "initials": None,
            "name": None,
            "organisation": row["organisation"],
            "email": None,
            "submitted_at": None,
            "category": None,
            "comment": None,
            "hidden": True,
        })
    return masked


def neighbours(publication, administration_id, search=None, status=None,
               agreement=None, page_size=None):
    """Prev/next ids and the queue page holding this Inkhundla.

    Computed over the whole filtered set **ignoring pagination**, so Next
    walks off the end of one page onto the next — page boundaries are a
    display artefact of the table, not a property of the queue.

    The current row is folded into the list even when the filter excludes it:
    validate an Inkhundla on the *Ready* tab and it becomes `validated`, so
    `?status=ready` stops matching it and Prev/Next would otherwise dead-end
    on the next reload.
    """
    rows = ordered_rows(
        publication, search=search, status=status, agreement=agreement
    )
    if all(r["administration_id"] != administration_id for r in rows):
        current = next(
            (
                r for r in ordered_rows(publication)
                if r["administration_id"] == administration_id
            ),
            None,
        )
        if current:
            rows = sorted(
                rows + [current], key=lambda r: (r["label"] or "").lower()
            )

    ids = [r["administration_id"] for r in rows]
    if administration_id not in ids:
        return {
            "prev_administration_id": None,
            "next_administration_id": None,
            "queue_page": None,
        }

    index = ids.index(administration_id)
    size = page_size or Pagination.page_size
    return {
        "prev_administration_id": ids[index - 1] if index > 0 else None,
        "next_administration_id": (
            ids[index + 1] if index < len(ids) - 1 else None
        ),
        "queue_page": index // size + 1,
    }


def sync_validated_values(publication, administration_id, category):
    """Mirror one submitted decision into the published projection.

    Upserts against ``initial_values``, never by mapping over
    ``validated_values`` — that field is null on a fresh publication, so
    mapping over it yields nothing and the write silently no-ops.
    """
    existing = {
        entry["administration_id"]: entry
        for entry in (publication.validated_values or [])
    }
    existing[administration_id] = {
        **existing.get(administration_id, {}),
        "administration_id": administration_id,
        "category": category,
    }
    publication.validated_values = [
        existing.get(
            entry["administration_id"],
            {"administration_id": entry["administration_id"],
             "category": None},
        )
        for entry in (publication.initial_values or [])
    ]
    publication.save(update_fields=["validated_values"])


@transaction.atomic
def save_decision(publication, administration, user, data, majority, is_tie):
    """Persist a draft, or submit — the two differ by one boolean.

    On submit the majority is **re-snapshotted**: a corrected category judged
    against a stale majority would give a simply wrong ``is_override``.
    """
    is_draft = data.get("is_draft", True)
    fields = {
        "category": data.get("category"),
        "reasoning": data.get("reasoning") or None,
        "is_draft": is_draft,
    }
    if not is_draft:
        fields.update({
            "majority_category": majority,
            "is_override": data["category"] != majority,
            "validated_by": user,
            "validated_at": timezone.now(),
        })

    decision, _ = ValidationDecision.objects.update_or_create(
        publication=publication, administration=administration,
        defaults=fields,
    )
    if not is_draft:
        sync_validated_values(
            publication, administration.id, decision.category
        )
    return decision


def bulk_reasoning(spread):
    """Generated rationale for a bulk-validated row.

    Bulk asks the admin for nothing, so leaving `reasoning` null would make
    every bulk row read as an omission in Decision history months later. The
    fixed prefix is what an audit greps for (D-8).
    """
    return (
        f"{BULK_REASONING_PREFIX} all {len(spread)} reviewers agreed on "
        f"{DroughtCategory.FieldStr.get(spread[0], spread[0])}."
    )


@transaction.atomic
def bulk_validate(publication, user, search=None):
    """Validate every ready + undisputed Inkhundla in one transaction.

    The target set is re-derived here rather than accepted from the client, so
    a reviewer submitting a dissenting class between render and click drops
    that row from the write instead of corrupting it (TC-3). `status` is
    forced to `ready` whatever the caller asked for: a hand-edited query
    string must not be able to widen a write the admin never saw (D-3).

    Rows that already carry a decision are skipped, not overwritten. A ready
    row can never be *validated* already — `row_status` gives validated
    precedence — but it can hold a **draft**, and silently discarding an
    admin's part-written reasoning is invisible data loss (D-5).
    """
    rows = ordered_rows(
        publication,
        search=search,
        status=ValidationStatus.ready,
        agreement=AgreementFilter.undisputed,
    )
    decided = set(
        ValidationDecision.objects
        .filter(publication=publication)
        .values_list("administration_id", flat=True)
    )
    targets = [r for r in rows if r["administration_id"] not in decided]

    administrations = {
        a.id: a
        for a in Administration.objects.filter(
            id__in=[r["administration_id"] for r in targets]
        )
    }
    for row in targets:
        spread = row["dclass_spread"]
        category = spread[0]
        # ponytail: one JSON rewrite per row via sync_validated_values — fine
        # at 59 Tinkhundla, batch into a single sync if that count ever grows.
        save_decision(
            publication,
            administrations[row["administration_id"]],
            user,
            {
                "category": category,
                "reasoning": bulk_reasoning(spread),
                "is_draft": False,
            },
            # Unanimous, so the majority IS the category and `is_override`
            # computes to False. Passed explicitly rather than recomputed so
            # this reads as the same contract the decision PUT satisfies.
            majority=category,
            is_tie=False,
        )
    return {
        "validated": len(targets),
        "skipped_drafts": len(rows) - len(targets),
    }


def build_decision_payload(publication, row, reviews, masked):
    """The single-Inkhundla payload, assembled from parts that already exist.

    Keys the shipped page already reads keep their names and nesting; new
    fields sit alongside. Every deviation is a frontend change, so there are
    as few as possible.
    """
    categories = [
        r["category"] for r in reviews if is_validated(r.get("category"))
    ]
    agreement = None if masked else build_agreement(categories)
    majority = (
        None if masked else majority_of(categories)[0]
    )
    decision = ValidationDecision.objects.filter(
        publication=publication, administration_id=row["administration_id"]
    ).first()

    return {
        "administration_id": row["administration_id"],
        "label": row["label"],
        "region": row["group"],
        "zone": row.get("zone"),
        "status": row["status"],
        "awaiting_count": row["awaiting_count"],
        "reviews_completed": row["reviews_completed"],
        "reviews_total": row["reviews_total"],
        "consensus": None if masked else consensus(categories),
        "majority_category": majority,
        "validated_category": row["validated_category"],
        "confidence": row.get("confidence"),
        "confidence_band": row.get("confidence_band"),
        "confidence_is_mock": True,
        "is_override": bool(decision.is_override) if decision else False,
        "masked": masked,
        "agreement": agreement,
        "reviews": reviews,
        "decision": {
            "category": decision.category,
            "reasoning": decision.reasoning,
            "is_draft": decision.is_draft,
            "updated_at": decision.updated_at,
        } if decision else None,
    }


def build_meta(publication, request_user, neighbour_data):
    """`meta` block: the publish-adjacent context the page needs."""
    can_submit = request_user.role == UserRoleTypes.admin
    return {
        "publication_id": publication.id,
        "year_month": publication.year_month.strftime("%Y-%m"),
        "reviewers_required": reviewers_required(publication),
        "can_submit": can_submit,
        "viewer": {
            "name": request_user.name,
            "organisation": request_user.technical_working_group,
        },
        **neighbour_data,
    }


def build_history(publication, administration_id, limit=6):
    """Submitted decisions from **earlier** cycles, newest first (AC-7.1)."""
    rows = (
        ValidationDecision.objects
        .filter(
            administration_id=administration_id,
            is_draft=False,
            publication__year_month__lt=publication.year_month,
        )
        .select_related("publication", "validated_by")
        .order_by("-publication__year_month")[:limit]
    )
    return [
        {
            "id": row.id,
            "year_month": row.publication.year_month.strftime("%Y-%m"),
            "category": row.category,
            "is_override": row.is_override,
            "reasoning": row.reasoning,
            "initials": (
                initials(row.validated_by.name) if row.validated_by else None
            ),
            "name": row.validated_by.name if row.validated_by else None,
            "validated_at": row.validated_at,
        }
        for row in rows
    ]


__all__ = [
    "build_agreement",
    "build_decision_payload",
    "build_history",
    "build_meta",
    "build_reviews",
    "consensus_band",
    "has_submitted",
    "majority_of",
    "mask_reviews",
    "neighbours",
    "save_decision",
    "sync_validated_values",
]
