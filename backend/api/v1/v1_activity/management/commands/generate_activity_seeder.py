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
_STATUS_BY_NAME = {
    "draft": ActivityStatus.draft,
    "active": ActivityStatus.active,
    "archived": ActivityStatus.archived,
}

# Demo rows live in the same CSV as the real NDMA library but ship as `draft`,
# so they are inert until --demo activates them (DEMO-1).
#
# Their triggers are calibrated against what the Indicator table ACTUALLY
# holds. `cattle` and `water_demand` are null for all 59 Tinkhundla and
# _condition_pass fails on None, so the real library's cattle/water thresholds
# can never fire — the demo rows gate on dclass, ipc_phase, population,
# cropland and land_use_dvi_agri, which are populated everywhere.
#
# ACT-DEMO-COORD-1 is deliberately class 0, so at least one activity fires for
# EVERY Inkhundla, including the wet/normal ones, and no Inkhundla renders
# "no activities triggered". The rest use higher thresholds so per-sector
# counts differ — a uniform 59 everywhere would hide the trigger logic.
DEMO_CODE_PREFIX = "ACT-DEMO-"


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
        parser.add_argument(
            "--demo",
            action="store_true",
            help=(
                "Activate the ACT-DEMO-* rows, whose triggers are calibrated "
                "to fire against the latest published map. Re-run without it "
                "to put them back to draft."
            ),
        )

    def handle(self, *args, **options):
        demo = options.get("demo", False)

        with open("./source/activity_library.csv", newline="") as fh:
            rows = list(csv.DictReader(fh))

        activated = 0
        for row in rows:
            code = row["code"].strip()
            status = _STATUS_BY_NAME.get(
                (row.get("status") or "").strip(), ActivityStatus.active
            )
            if code.startswith(DEMO_CODE_PREFIX):
                # --demo is a toggle, not an append: without it the demo rows
                # are reset to draft, so the National overview goes back to
                # the real library alone.
                status = (
                    ActivityStatus.active if demo else ActivityStatus.draft
                )
                activated += int(demo)

            ResponseActivity.objects.update_or_create(
                code=code,
                defaults={
                    "title": row["title"].strip(),
                    "description": (
                        row.get("description") or "").strip() or None,
                    "sector": _SECTOR_BY_CODE[row["sector"].strip()],
                    "status": status,
                    "owner": (row.get("owner") or "").strip() or None,
                    "coord_with": (row.get("coord_with") or "").strip() or None,
                    "response_type": _RESPONSE_BY_NAME.get(
                        (row.get("response_type") or "").strip()),
                    "source_doc": (row.get("source_doc") or "").strip() or None,
                    "triggers": _compose_triggers(row),
                },
            )

        if not options.get("test"):
            suffix = (  # pragma: no cover
                f" ({activated} demo rows activated)" if demo else ""
            )
            self.stdout.write(self.style.SUCCESS(  # pragma: no cover
                f"Seeded {len(rows)} Response Activities{suffix}."))
