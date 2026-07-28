"""CDI Explorer (INS-3) read helpers.

Everything here is derived from PUBLISHED publications only (design D-4). The
D-class strip, the metric cards and the four charts must share one window and
one "latest month": component rasters are extracted at publication *create*
time, so an unpublished month already has indicator values in the database and
serving them would both leak a map still under review and run the charts a
month ahead of the strip beside them.
"""
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


def latest_published_month():
    """The newest published month as 'YYYY-MM', or None."""
    year_month = (
        Publication.objects.filter(
            status=PublicationStatus.published, published_at__isnull=False
        )
        .order_by("-year_month")
        .values_list("year_month", flat=True)
        .first()
    )
    return as_target_month(year_month) if year_month else None


def resolve_window(from_month: str = None, to_month: str = None):
    """(from_period, to_period), or (None, None) when nothing is published
    yet and no explicit range was given.

    The default is the last CDI_EXPLORER_DEFAULT_MONTHS months ending at the
    latest PUBLISHED month (design D-11) — anchored on publication rather than
    on today, because CDI publishes 1-2 months in arrears and a
    calendar-year-to-date default would return a mostly empty strip.
    """
    end = to_month or latest_published_month()
    if not end:
        return None, None
    start = from_month or shift_period(end, -(CDI_EXPLORER_DEFAULT_MONTHS - 1))
    # Capped here rather than in the query serializer: with only `from`
    # supplied the span is not knowable until `to` has fallen back to the
    # latest published month.
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
            meta["reason"] = "no_raster_data"
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
    from_period, to_period = resolve_window()
    if not from_period:
        base["data"] = None
        base["breakdown"] = None
        base["meta"] = {"reason": "no_published_data"}
        return base

    publications = published_in_window(from_period, to_period)
    periods = month_range(from_period, to_period)
    values = raster_values(publications, administration.pk, ALL_INDICATORS)
    categories = {
        as_target_month(publication.year_month): _pluck(
            publication.validated_values, administration.pk, "category"
        )
        for publication in publications
    }
    # The window ends at the latest published month, so the last two entries
    # are the two most recent published months. Adjacent in this list, not
    # necessarily adjacent in the calendar — previous_period says which.
    latest = publications[-1]
    previous = publications[-2] if len(publications) > 1 else None

    base["data"] = build_cards(
        as_target_month(latest.year_month),
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
        "period": as_target_month(latest.year_month),
        "last_updated": latest.published_at,
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
    if not from_period:
        base["data"] = None
        base["meta"] = {"reason": "no_published_data"}
        return base

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
