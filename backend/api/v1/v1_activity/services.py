import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from api.v1.v1_activity.models import ResponseActivity, ActivityHistory
from api.v1.v1_activity.constants import (
    ActivityStatus,
    ActivitySector,
    TriggerOperator,
    DCLASS_SEGMENT,
    ACTIVITY_TRANSITIONS,
)

_VERSION_RE = re.compile(r"^v(\d+)\.(\d+)$")


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
