"""The "Situation this period" draft (BB-3 D-2).

Composes a narrative from platform data, one clause per source. A clause whose
source is silent is DROPPED, never softened — no "data suggests", no invented
figure. `meta.sources` names the clauses that fired, so a reviewer can see what
the draft rests on and an omission is auditable rather than invisible.

The prose is a starting point, not a record: the frontend marks it "Suggested
draft" off `meta.generated` and the user rewrites it in place.
"""

from api.v1.v1_iks.utils import active_kobo_data, active_values
from api.v1.v1_risk_level.constants import TREND_DESC
from api.v1.v1_risk_level.service import compute_risk_level_detail

# Section C of the IKS form is the extreme-weather block (mirrors IKSStatsView's
# own section split).
EXTREME_WEATHER_SECTION = "C"


def _period_label(period):
    """"2026-05" -> "May 2026". Returns None for a missing/odd period."""
    try:
        year, month = period.split("-")
        from calendar import month_name

        return f"{month_name[int(month)]} {year}"
    except (AttributeError, ValueError, IndexError):
        return None


def _dclass_clause(name, detail):
    d_class = detail["drought"]["key"]
    label = _period_label(detail["period"])
    if not d_class or not label:
        return None
    return f"{name} is validated at {d_class} for {label}."


def _trend_clause(detail):
    """`trend` is the direction of the most recent cycle-to-cycle step, which
    is exactly what this sentence claims. `trend_desc` is NOT usable here — it
    is a phrase ("1 month unchanged"), not an adjective."""
    trend = detail["drought"].get("trend")
    if not trend:
        return None
    return (
        f"Conditions are {TREND_DESC[trend]} against the previous cycle."
    )


def _iks_counts(administration_id, period):
    """(reports, extreme-weather signals) submitted in `period`.

    Both are plain counts over the active KoboForm's data — the only IKS
    figures that are genuinely derived. `form_completion_percentage` and
    `average_validation_time_days` are backed by MOCK_* constants and are
    deliberately not read here (BB-3 D-7).
    """
    year, month = period.split("-")
    submissions = active_kobo_data().filter(
        submission_time__year=int(year),
        submission_time__month=int(month),
    )
    kobo_ids = set(
        active_values()
        .filter(administration_id=administration_id)
        .values_list("kobo_id", flat=True)
    )
    cycle_ids = set(
        submissions.filter(kobo_id__in=kobo_ids).values_list(
            "kobo_id", flat=True
        )
    )
    if not cycle_ids:
        return 0, 0

    extreme = (
        active_values()
        .filter(
            administration_id=administration_id,
            kobo_id__in=cycle_ids,
            iks_indicator__section=EXTREME_WEATHER_SECTION,
        )
        .values_list("kobo_id", flat=True)
        .distinct()
        .count()
    )
    return len(cycle_ids), extreme


def _iks_clause(administration_id, period):
    if not period:
        return None
    reports, extreme = _iks_counts(administration_id, period)
    if not reports:
        return None
    plural = "" if reports == 1 else "s"
    sentence = f"{reports} IKS observer report{plural} received this cycle"
    if extreme == reports:
        sentence += ", flagging extreme-weather indicators"
    elif extreme:
        sentence += f", {extreme} of them flagging extreme-weather indicators"
    return f"{sentence}."


def build_situation(administration) -> dict:
    """The draft, plus which sources it actually used."""
    detail = compute_risk_level_detail(administration)
    period = detail["period"]

    # ponytail: no rainfall clause yet. It needs AdministrationObservation
    # (real CHIRPS mm per Inkhundla), which WX-10 designs but has not shipped.
    # A station-based interim is deliberately NOT built — WX-10 measured the
    # within-region satellite spread at 25-135 mm against a real delta of
    # ~0.6 mm, so a station-anchored figure would say more about which
    # Inkhundla was picked than about the weather (BB-3 D-5).
    clauses = [
        ("dclass", _dclass_clause(administration.name, detail)),
        ("trend", _trend_clause(detail)),
        ("iks", _iks_clause(administration.pk, period)),
    ]
    fired = [(key, text) for key, text in clauses if text]

    return {
        "administration": {
            "id": administration.pk,
            "name": administration.name,
        },
        "period": period,
        "meta": {
            "generated": True,
            "editable": True,
            "sources": [key for key, _ in fired],
        },
        "value": " ".join(text for _, text in fired),
    }
