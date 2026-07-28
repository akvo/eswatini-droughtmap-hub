"""CDI Explorer (INS-3) read helpers.

Everything here is derived from PUBLISHED publications only (design D-4). The
D-class strip, the metric cards and the four charts must share one window and
one "latest month": component rasters are extracted at publication *create*
time, so an unpublished month already has indicator values in the database and
serving them would both leak a map still under review and run the charts a
month ahead of the strip beside them.
"""
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from api.v1.v1_publication.constants import (
    CDI_EXPLORER_DEFAULT_MONTHS,
    CDI_EXPLORER_MAX_MONTHS,
    PCT_RANK_UNITS,
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.utils import as_target_month
from utils.periods import month_range, month_start, period_span, shift_period

ALL_INDICATORS = list(RasterIndicatorTypes.FieldStr)


def has_published_publication() -> bool:
    return Publication.objects.filter(
        status=PublicationStatus.published, published_at__isnull=False
    ).exists()


def current_period() -> str:
    return as_target_month(timezone.now().date())


def resolve_window(from_month: str = None, to_month: str = None):
    """(from_period, to_period) — always a real window.

    The default is the last CDI_EXPLORER_DEFAULT_MONTHS calendar months ending
    at the CURRENT month, so the strip reads as "the last year" and lines up
    with the IKS monthly grids beside it.

    Deliberately NOT anchored on the latest published month (the original D-11
    choice): that made the axis a function of the data, so a database whose
    newest published map is old — a fresh environment seeded with historical
    months, or a long publication pause — rendered a strip labelled with those
    old years instead of recent ones. Publication lag now shows up the honest
    way, as empty cells on the right.
    """
    end = to_month or current_period()
    start = from_month or shift_period(end, -(CDI_EXPLORER_DEFAULT_MONTHS - 1))
    # Capped here rather than in the query serializer: with only `from`
    # supplied the span is not knowable until `to` has fallen back to the
    # current month.
    if period_span(start, end) > CDI_EXPLORER_MAX_MONTHS:
        raise ValidationError(
            f"Range too large (max {CDI_EXPLORER_MAX_MONTHS} months)"
        )
    return start, end


def published_in_window(from_period: str, to_period: str) -> list:
    return list(
        Publication.objects.filter(
            status=PublicationStatus.published,
            published_at__isnull=False,
            year_month__range=(
                month_start(from_period),
                month_start(to_period),
            ),
        ).order_by("year_month")
    )


def _pluck(items, administration_id, field):
    """One Inkhundla's entry out of a ~59-item per-publication JSON blob."""
    return next(
        (
            item.get(field)
            for item in (items or [])
            if item.get("administration_id") == administration_id
        ),
        None,
    )


def raster_values(publications, administration_id, indicators) -> dict:
    """{(period, indicator): value} for the window, in one query.

    ponytail: the `values` column is a ~59-item JSON blob scanned in Python.
    Worst case here is 4 indicators x 120 months = 480 blobs, still trivial.
    The ceiling is a NATIONAL view (all 59 Tinkhundla in one response), which
    would scan 59x this per request — that is when a publication_raster_values
    table earns its migration.
    """
    rows = PublicationRaster.objects.filter(
        publication__in=publications, indicator__in=indicators
    ).values_list("publication__year_month", "indicator", "values")
    return {
        (as_target_month(year_month), indicator): _pluck(
            values, administration_id, "value"
        )
        for year_month, indicator, values in rows
    }


def current_dclass(administration):
    """This Inkhundla's drought class from the latest PUBLISHED map.

    Lives here rather than in v1_weather (design D-6): every Detailed Insights
    tab renders the same chip, so the rule needs exactly one definition and it
    belongs beside the model it reads. Labels and colors stay in frontend
    config (CLAUDE.md). None when no published month covers this Inkhundla.
    """
    publication = (
        Publication.objects.filter(
            status=PublicationStatus.published,
            validated_values__isnull=False,
        )
        .order_by("-year_month")
        .first()
    )
    if not publication:
        return None
    category = _pluck(
        publication.validated_values, administration.pk, "category"
    )
    if category is None:
        return None
    return {
        "category": category,
        "period": as_target_month(publication.year_month),
    }


def _change_pct(value, previous):
    """Signed percent change, or None when there is no meaningful ratio.

    Deliberately None rather than 0 when the previous month is missing or
    zero — the card then omits its delta row instead of claiming "no change"
    (design D-8). Direction (arrow, color) is derived from the sign by the
    frontend.
    """
    if value is None or not previous:
        return None
    return round((value - previous) / previous * 100, 1)


def build_cards(period, previous_period, values, indicators) -> list:
    cards = []
    for indicator in indicators:
        value = values.get((period, indicator))
        previous = (
            values.get((previous_period, indicator))
            if previous_period
            else None
        )
        meta = {
            "period": period,
            "previous": previous,
            "previous_period": (
                previous_period if previous is not None else None
            ),
            "change_pct": _change_pct(value, previous),
        }
        if value is None:
            # Distinguish "this index has no raster for the latest published
            # month" from "nothing was published in the window at all" — the
            # first is a gap in one dataset, the second is a gap in the map.
            meta["reason"] = (
                "no_raster_data" if period else "no_published_data_in_window"
            )
        cards.append(
            {
                "key": indicator,
                "label": RasterIndicatorTypes.FieldStr[indicator],
                "value": value,
                "units": PCT_RANK_UNITS,
                "meta": meta,
            }
        )
    return cards


def build_series(periods, values, indicators) -> list:
    return [
        {
            "key": indicator,
            "label": RasterIndicatorTypes.FieldStr[indicator],
            "units": PCT_RANK_UNITS,
            "data": [
                {"period": period, "value": values.get((period, indicator))}
                for period in periods
            ],
        }
        for indicator in indicators
    ]


def _base(administration) -> dict:
    return {
        "key": administration.pk,
        "label": administration.name,
        "group": administration.region,
    }


def administration_stats(administration) -> dict:
    """Header context + D-class history strip + the four metric cards.

    Range-independent, so the frontend fetches it once per Inkhundla while
    /series re-fetches on every picker change (design D-2).
    """
    base = _base(administration)
    base["value"] = {
        "zone": administration.zone,
        "dclass": current_dclass(administration),
    }
    if not has_published_publication():
        base["data"] = None
        base["breakdown"] = None
        base["meta"] = {"reason": "no_published_data"}
        return base

    from_period, to_period = resolve_window()
    publications = published_in_window(from_period, to_period)
    periods = month_range(from_period, to_period)
    values = raster_values(publications, administration.pk, ALL_INDICATORS)
    categories = {
        as_target_month(publication.year_month): _pluck(
            publication.validated_values, administration.pk, "category"
        )
        for publication in publications
    }
    # The two most recent published months IN THE WINDOW. Adjacent in this
    # list, not necessarily adjacent in the calendar — previous_period says
    # which. Both may be absent: the window is anchored on today, so a
    # publication pause longer than the window leaves it empty, and that must
    # render as a blank strip rather than raise.
    latest = publications[-1] if publications else None
    previous = publications[-2] if len(publications) > 1 else None

    base["data"] = build_cards(
        as_target_month(latest.year_month) if latest else None,
        as_target_month(previous.year_month) if previous else None,
        values,
        ALL_INDICATORS,
    )
    base["breakdown"] = {
        "group": "dclass_history",
        "data": [
            {"period": period, "value": categories.get(period)}
            for period in periods
        ],
    }
    base["meta"] = {
        "period": as_target_month(latest.year_month) if latest else None,
        "last_updated": latest.published_at if latest else None,
        "from": from_period,
        "to": to_period,
        "months": len(periods),
    }
    return base


def administration_series(
    administration, from_month=None, to_month=None, indicators=None
) -> dict:
    """The chart series. Each Figma chart owns its own date picker, so this is
    called once per chart with `indicators` narrowed to that chart's index."""
    base = _base(administration)
    indicators = indicators or ALL_INDICATORS
    from_period, to_period = resolve_window(from_month, to_month)
    publications = published_in_window(from_period, to_period)
    periods = month_range(from_period, to_period)
    values = raster_values(publications, administration.pk, indicators)
    base["data"] = build_series(periods, values, indicators)
    base["meta"] = {
        "from": from_period,
        "to": to_period,
        "months": len(periods),
        "indicators": indicators,
    }
    return base
