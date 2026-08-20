import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from api.v1.v1_activity.models import ResponseActivity, ActivityHistory
from api.v1.v1_activity.constants import (
    ActivityResponseType,
    ActivityStatus,
    ActivitySector,
    TriggerOperator,
    DCLASS_SEGMENT,
    ACTIVITY_TRANSITIONS,
)
from api.v1.v1_activity.trigger_evaluation import (
    build_dataset,
    activity_passes,
)

_VERSION_RE = re.compile(r"^v(\d+)\.(\d+)$")


def published_sector_ids():
    """Sector ids with at least one ACTIVE PUBLIC activity.

    These are exactly the sectors that render as cards on the National
    Overview, and therefore exactly the ones the publish modal must collect
    context for. Defined once so the modal, the overview and the publish
    validation cannot disagree about the list.
    """
    return sorted(
        set(
            ResponseActivity.objects.filter(
                status=ActivityStatus.active,
                response_type=ActivityResponseType.public,
            ).values_list("sector", flat=True)
        )
    )


def triggered_sector_ids():
    """Sector ids whose activities actually FIRE under the current map.

    A subset of published_sector_ids(): a sector can hold active public
    activities that trigger nowhere this month, because every one of them
    gates on a drought class the map does not reach. Those sectors still
    render a card (with 0 Tinkhundla), but their paragraph is not demanded
    of the admin — there is nothing to describe.

    Recomputed rather than stored: it depends on the published map, so it
    changes the moment a new one goes out.
    """
    dataset = build_dataset()
    triggered = set()
    activities = ResponseActivity.objects.filter(
        status=ActivityStatus.active,
        response_type=ActivityResponseType.public,
    ).exclude(triggers__isnull=True)
    for act in activities:
        if act.sector in triggered:
            continue  # one firing activity is enough for the sector
        if any(activity_passes(act.triggers, row)
               for row in dataset.values()):
            triggered.add(act.sector)
    return sorted(triggered)


def next_code(sector):
    """ACT-<SECTOR>-<seq>; seq counts all rows in the sector, incl.
    soft-deleted."""
    seq = ResponseActivity.objects_with_deleted.filter(
        sector=sector).count() + 1
    return f"ACT-{ActivitySector.Code[sector]}-{seq}"


def bump_minor(version):
    """v1.0 -> v1.1. Unparseable input falls back to v1.1."""
    match = _VERSION_RE.match(version or "")
    if not match:
        return "v1.1"
    major, minor = int(match.group(1)), int(match.group(2))
    return f"v{major}.{minor + 1}"


def derive_action_label(from_status, to_status):
    if from_status is None:
        return "Created draft"
    if from_status == to_status:
        return "Edited"
    if to_status == ActivityStatus.active:
        return "Activated"
    if to_status == ActivityStatus.archived:
        return "Archived"
    return "Updated"


def trigger_summary(triggers):
    """Human-readable one-line summary of a trigger, for lists and
    detail views."""
    if not triggers:
        return ""
    parts = []
    dclass = triggers.get("dclass") or {}
    cls = dclass.get("class")
    if cls:
        label = DCLASS_SEGMENT.get(cls, f"class {cls}")
        parts.append(f"{label}+ for {dclass.get('months', 1)} mo")
    vuln = triggers.get("vuln")
    if vuln:
        op = TriggerOperator.FieldStr[vuln["op"]]
        parts.append(f"IPC {op} Phase {vuln['value']}")
    for cond in triggers.get("exp") or []:
        op = TriggerOperator.FieldStr[cond["op"]]
        parts.append(f"{cond['indicator']} {op} {cond['value']}")
    other = triggers.get("other")
    if other:
        parts.append(other)
    return " · ".join(parts)


def apply_transition(activity, to_status, user, note=None):
    """Validate and perform a lifecycle transition, writing a history row."""
    if to_status not in ACTIVITY_TRANSITIONS.get(activity.status, []):
        raise ValidationError({"to_status": "Illegal transition."})
    from_status = activity.status
    with transaction.atomic():
        activity.status = to_status
        if to_status == ActivityStatus.active:
            activity.version = bump_minor(activity.version)
            activity.activated_by = user
            activity.activated_at = timezone.now()
        activity.save()
        ActivityHistory.objects.create(
            activity=activity, from_status=from_status,
            to_status=to_status, user=user, note=note)
    return activity


def preview_trigger(triggers):
    """How many administrations the draft trigger currently fires for.

    Runs the SAME predicate and dataset the recommended-actions endpoint
    uses, so the wizard preview and live firing can never diverge.
    """
    dataset = build_dataset()
    matched = sum(
        1 for row in dataset.values() if activity_passes(triggers, row))
    return {"matched": matched, "total": len(dataset)}
