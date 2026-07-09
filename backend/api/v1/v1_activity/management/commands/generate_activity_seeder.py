import csv

from django.core.management.base import BaseCommand

from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import (
    ActivityStatus, ActivitySector, ActivityResponseType, TriggerOperator)

# Reverse lookups from the human-readable CSV values to DB ints.
_SECTOR_BY_CODE = {v: k for k, v in ActivitySector.Code.items()}
_RESPONSE_BY_NAME = {
    "public": ActivityResponseType.public,
    "institutional": ActivityResponseType.institutional,
}
_OP_BY_NAME = {"gte": TriggerOperator.gte, "lte": TriggerOperator.lte}


def _int_or_none(value):
    value = (value or "").strip()
    return int(value) if value else None


def _op_or_none(value):
    value = (value or "").strip()
    return _OP_BY_NAME.get(value)


def _parse_exp(raw):
    """'population gte 2000;cattle gte 1500' -> list of condition dicts."""
    conditions = []
    for chunk in (raw or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        indicator, op, value = chunk.split()
        conditions.append({
            "indicator": indicator,
            "op": _OP_BY_NAME[op],
            "value": float(value),
        })
    return conditions


def _compose_triggers(row):
    dclass_class = _int_or_none(row.get("trigger_dclass_class"))
    dclass = None
    if dclass_class is not None:
        dclass = {
            "class": dclass_class,
            "months": _int_or_none(row.get("trigger_dclass_months")) or 1,
        }
    vuln = None
    vuln_op = _op_or_none(row.get("trigger_vuln_op"))
    vuln_value = _int_or_none(row.get("trigger_vuln_value"))
    if vuln_op and vuln_value is not None:
        vuln = {"op": vuln_op, "value": vuln_value}
    other = (row.get("trigger_other") or "").strip() or None
    return {
        "dclass": dclass,
        "vuln": vuln,
        "exp": _parse_exp(row.get("trigger_exp")),
        "other": other,
    }


class Command(BaseCommand):
    help = "Seed Response Activities from source/activity_library.csv."

    def add_arguments(self, parser):
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
        )

    def handle(self, *args, **options):
        with open("./source/activity_library.csv", newline="") as fh:
            rows = list(csv.DictReader(fh))

        for row in rows:
            ResponseActivity.objects.update_or_create(
                code=row["code"].strip(),
                defaults={
                    "title": row["title"].strip(),
                    "description": (
                        row.get("description") or "").strip() or None,
                    "sector": _SECTOR_BY_CODE[row["sector"].strip()],
                    "status": ActivityStatus.active,
                    "owner": (row.get("owner") or "").strip() or None,
                    "coord_with": (row.get("coord_with") or "").strip() or None,
                    "response_type": _RESPONSE_BY_NAME.get(
                        (row.get("response_type") or "").strip()),
                    "source_doc": (row.get("source_doc") or "").strip() or None,
                    "triggers": _compose_triggers(row),
                },
            )

        if not options.get("test"):
            self.stdout.write(self.style.SUCCESS(  # pragma: no cover
                f"Seeded {len(rows)} Response Activities."))
