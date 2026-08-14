import logging
from collections import Counter, defaultdict
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from api.v1.v1_publication.models import Publication, Administration
from api.v1.v1_publication.constants import (
    PublicationStatus,
    DroughtCategory,
    AdministrationZones,
    is_validated,
)
from api.v1.v1_insights.constants import LAYERS, METRICS_HISTORY_MONTHS
from api.v1.v1_insights.drought_aggregation import modal_category
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    WeatherStation,
)
from api.v1.v1_weather.services import (
    administration_deviation,
    national_deviation,
    station_health,
)
from utils.periods import shift_period
from api.v1.v1_iks.utils import active_kobo_data, active_values
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import (
    ActivityStatus,
    ActivityResponseType,
    ActivitySector,
)
from api.v1.v1_activity.trigger_evaluation import (
    build_dataset,
    activity_passes,
)

logger = logging.getLogger(__name__)


def _latest_value(series):
    """Most recent non-null point, or None.

    Walked backwards rather than taking series[-1]: the current month often
    has no complete observation yet, and reporting its null as the headline
    figure would blank a card that has eleven good months behind it.
    """
    for item in reversed(series):
        if item["value"] is not None:
            return item["value"]
    return None


SECTOR_MAP = {
    ActivitySector.wash: ("water", "Water and Sanitation"),
    ActivitySector.food: ("agriculture", "Agriculture and Food security"),
    ActivitySector.env: ("environment", "Environment and energy"),
    ActivitySector.health: ("health", "Health and nutrition"),
}


def compute_linear_slope(series):
    """
    Calculate slope for series [(month_str, float_val)].
    Returns 'worsening', 'improving', 'stable' or 'unknown'.

    Fewer than two readings is 'unknown', not 'stable': with nothing to
    compare against, "stable" claims the drought level held steady when in
    fact no trend was ever measured.
    """
    if len(series) < 2:
        return "unknown"
    n = len(series)
    x = list(range(n))
    y = [val for _, val in series]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return "stable"
    slope = num / den
    if slope > 0.05:
        return "worsening"
    elif slope < -0.05:
        return "improving"
    return "stable"


def get_hero_data():
    """Service for GET /api/v1/insights/hero"""
    pub = (
        Publication.objects.filter(
            status=PublicationStatus.published, published_at__isnull=False
        )
        .order_by("-year_month", "-id")
        .first()
    )

    if not pub:
        return {
            "status": {
                "category": DroughtCategory.none,
                "label": DroughtCategory.FieldStr.get(DroughtCategory.none),
            },
            "period": None,
            "published": "-",
            "nextUpdate": "-",
            "headline": "Drought situation overview — No active publication",
            "summary": "No published drought map is currently available.",
        }

    cats = []
    if pub.validated_values:
        cats = [
            item["category"]
            for item in pub.validated_values
            if item.get("category") is not None
            and item.get("category") != -9999
        ]
    avg_cat = round(sum(cats) / len(cats)) if cats else 0
    label = DroughtCategory.FieldStr.get(avg_cat, "Normal / No Drought")

    published_str = (
        pub.published_at.strftime("%d %b %Y")
        if pub.published_at
        else pub.year_month.strftime("%b %Y")
    )
    next_update_dt = (pub.published_at or pub.created_at) + relativedelta(
        months=1
    )
    next_update_str = next_update_dt.strftime("%d %b %Y")

    month_year_str = pub.year_month.strftime("%B %Y")
    headline = f"Drought situation overview — {month_year_str}"
    summary = pub.narrative or ""

    return {
        "status": {"category": avg_cat, "label": label},
        # The CDI period the overview describes, for the PDF export filename.
        # Distinct from `published`, which is when it went out — they differ
        # whenever publication lags the month it covers, i.e. usually.
        "period": pub.year_month.strftime("%Y-%m"),
        "published": published_str,
        "nextUpdate": next_update_str,
        "headline": headline,
        "summary": summary,
    }


def get_zones_data(group="regions"):
    """Service for GET /api/v1/insights/zones?group=regions|climatic"""
    published = Publication.objects.filter(
        status=PublicationStatus.published, published_at__isnull=False
    )
    latest_pub = published.order_by("-year_month", "-id").first()

    # No publication means no period — the current month would read as a
    # bulletin that does not exist.
    period_str = latest_pub.year_month.strftime("%Y-%m") if latest_pub else None

    # Fetch last 6 published publications
    recent_pubs = list(published.order_by("-year_month", "-id")[:6])
    recent_pubs.reverse()  # chronological

    admins = list(Administration.objects.all())

    # Build groupings
    groups_map = {}
    if group == "climatic":
        for i, (zone_val, zone_label) in enumerate(
            AdministrationZones.choices(), start=101
        ):
            zone_admins = [a for a in admins if a.zone == zone_val]
            if zone_admins:
                groups_map[zone_val] = {
                    "id": i,
                    "label": zone_label,
                    "admins": zone_admins,
                }

    else:  # regions
        regions = set(a.region for a in admins if a.region)
        for i, reg_name in enumerate(sorted(regions), start=1):
            reg_admins = [a for a in admins if a.region == reg_name]
            groups_map[reg_name] = {
                "id": i,
                "label": reg_name,
                "admins": reg_admins,
            }

    zones_list = []
    trends_list = []
    breakdowns_list = []

    # Only real, admin-assigned D-classes land here. An Inkhundla with no
    # published category is simply absent — never defaulted to 0, which the
    # frontend paints as a genuine "Wet/normal conditions" verdict.
    latest_vals = {}
    if latest_pub and latest_pub.validated_values:
        latest_vals = {
            v["administration_id"]: v["category"]
            for v in latest_pub.validated_values
            if is_validated(v.get("category"))
        }

    for g_key, g_info in groups_map.items():
        g_id = g_info["id"]
        g_label = g_info["label"]
        g_admins = g_info["admins"]
        admin_ids = [a.id for a in g_admins]

        # Modal category over the Tinkhundla that actually have a published
        # category; confidence stays a share of the whole group, so missing
        # data shows up as low confidence rather than silent agreement.
        cat_counts = Counter(
            latest_vals[aid] for aid in admin_ids if aid in latest_vals
        )
        total_count = len(admin_ids) or 1
        modal_cat, confidence_pct = modal_category(cat_counts, total_count)

        zones_list.append(
            {
                "id": g_id,
                "label": g_label,
                "value": modal_cat,
                "confidence": confidence_pct,
            }
        )

        # Breakdowns
        names_by_cat = defaultdict(list)
        for adm_obj in g_admins:
            if not adm_obj.name:
                continue
            cat = latest_vals.get(adm_obj.id, DroughtCategory.none)
            names_by_cat[cat].append(adm_obj.name)

        no_data_count = total_count - sum(cat_counts.values())
        breakdown_counts = [
            {
                "key": c,
                "value": cat_counts.get(c, None),
                "names": names_by_cat.get(c, []),
            }
            for c in range(6)
        ]
        # Its own slice, so an unpublished group reads as "No Data" instead of
        # disappearing from the doughnut.
        breakdown_counts.append(
            {
                "key": DroughtCategory.none,
                "value": no_data_count or None,
                "names": names_by_cat.get(DroughtCategory.none, []),
            }
        )
        breakdowns_list.append(
            {
                "administration_id": g_id,
                "group": "tinkhundla",
                "data": breakdown_counts,
            }
        )

        # Trends. Months with no published category for this group are left
        # out of the series entirely — scoring them 0 would both invent a
        # "Normal" reading and drag the slope toward "improving".
        admin_id_set = set(admin_ids)
        series = []
        for p in recent_pubs:
            p_cats = [
                v["category"]
                for v in (p.validated_values or [])
                if v.get("administration_id") in admin_id_set
                and is_validated(v.get("category"))
            ]
            if not p_cats:
                continue
            mean_val = round(sum(p_cats) / len(p_cats), 1)
            series.append((p.year_month.strftime("%Y-%m"), mean_val))

        slope_trend = compute_linear_slope(series)
        trends_list.append(
            {
                "administration_id": g_id,
                "value": slope_trend,
                "method": "cdi-mean-slope",
                "group": "months",
                "data": [{"key": k, "value": v} for k, v in series],
            }
        )

    return {
        "zones": {"group": group, "period": period_str, "data": zones_list},
        "trends": {"group": group, "data": trends_list},
        "breakdowns": {"group": group, "data": breakdowns_list},
    }


def get_metrics_data(inkhundla_id=None):
    """Service for GET /api/v1/insights/metrics"""
    now = timezone.now()
    cutoff_30d = now - timedelta(days=30)

    admin = None
    if inkhundla_id:
        admin = Administration.objects.filter(id=inkhundla_id).first()

    # Weather Stations health
    all_stations = WeatherStation.objects.filter(is_active=True)
    if admin and admin.region:
        stations_in_region = all_stations.filter(region=admin.region)
        if stations_in_region.exists():
            all_stations = stations_in_region

    total_stations = all_stations.count()
    online_count = 0
    offline_count = 0
    degraded_count = 0

    for st in all_stations:
        st_h = station_health(st)
        if st_h["status"] == "online":
            online_count += 1
        elif st_h["status"] == "offline":
            offline_count += 1
        else:
            degraded_count += 1

    online_pct = (
        round((online_count / total_stations * 100))
        if total_stations > 0
        else 0
    )

    # Field Reports (Kobo 30d). Scoped through the `active_*` readers like
    # every other IKS surface, so a deactivated form's submissions never leak
    # into a public count.
    kobo_qs = active_kobo_data().filter(submission_time__gte=cutoff_30d)
    if admin:
        # Attributed through IKSValue.administration — the same join the IKS
        # explorer uses. The previous substring match on the raw JSON blob
        # matched a name appearing in ANY answer, and fell back to the
        # NATIONAL count whenever an Inkhundla had none of its own, so an
        # Inkhundla with no reports showed the country's total under its name.
        kobo_ids = (
            active_values()
            .filter(administration=admin)
            .values_list("kobo_id", flat=True)
        )
        kobo_qs = kobo_qs.filter(kobo_id__in=kobo_ids)

    kobo_count = kobo_qs.count()

    # Rainfall & Temperature deviation, last 12 CALENDAR months.
    #
    # The axis is calendar months, not published-publication months (D-12/Q1a).
    # These are weather series: a month with no publication would punch a hole
    # that has nothing to do with weather, and with a review backlog seeded by
    # --publish-through the chart would silently halve.
    to_period = now.strftime("%Y-%m")
    from_period = shift_period(to_period, -(METRICS_HISTORY_MONTHS - 1))

    if admin:
        rain_series = administration_deviation(
            admin, WeatherParameter.precipitation, from_period, to_period
        )
        temp_series = administration_deviation(
            admin, WeatherParameter.tmean, from_period, to_period
        )
    else:
        rain_series = national_deviation(
            WeatherParameter.precipitation, from_period, to_period
        )
        temp_series = national_deviation(
            WeatherParameter.tmean, from_period, to_period
        )

    rainfall_history = [
        {"key": item["period"], "value": item["value"]}
        for item in rain_series
    ]
    temp_history = [
        {"key": item["period"], "value": item["value"]} for item in temp_series
    ]
    latest_rain_dev = _latest_value(rain_series)
    latest_temp_dev = _latest_value(temp_series)

    month_note = now.strftime("%b %Y")
    if admin:
        month_note = f"{month_note} ({admin.name})"

    precip_label = "Precipitation vs 30-yr normal"
    temp_label = "Temperature vs 30 yr Normal"
    station_label = "Active stations"
    reports_label = "Field reports"

    if admin:
        precip_label = f"{precip_label} ({admin.name})"
        temp_label = f"{temp_label} ({admin.name})"
        reports_label = f"{reports_label} ({admin.name})"
        if admin.region:
            station_label = f"{station_label} ({admin.region})"

    return {
        "rainfall": {
            "value": latest_rain_dev,
            "unit": "mm",
            "note": f"{month_note} deviation",
            "label": precip_label,
            "history": rainfall_history,
        },
        "temperature": {
            "value": latest_temp_dev,
            "unit": "°C",
            # tmean, not Tmax: NORMALS_RASTERS only carries precipitation and
            # tmean, so a Tmax deviation is not computable — the old label
            # named a number that could never exist (DEMO-1 D-12).
            "note": f"{month_note} mean temperature deviation",
            "label": temp_label,
            "history": temp_history,
        },
        "activeStations": {
            "online": online_count,
            "total": total_stations,
            "onlinePct": online_pct,
            "label": station_label,
            "note": f"{offline_count} Offline  {degraded_count} Degraded",
        },
        "fieldReports": {
            "count": kobo_count,
            # Always None: nothing in the data model records whether a
            # submission was verified — no field, no workflow, nowhere. The
            # previous hardcoded 100 painted a full "verified" ring on a
            # public page for a check that never happened. `None` hides the
            # ring; give it a real value when a verification step exists.
            "verifiedPct": None,
            "label": reports_label,
            "note": "in last 30 days",
        },
    }


def get_response_activities_data():
    """Service for GET /api/v1/insights/response-activities"""
    latest_pub = (
        Publication.objects.filter(status=PublicationStatus.published)
        .order_by("-year_month", "-id")
        .first()
    )

    last_updated_str = (
        latest_pub.published_at.strftime("%d %b %Y")
        if (latest_pub and latest_pub.published_at)
        else timezone.now().strftime("%d %b %Y")
    )

    active_public_activities = ResponseActivity.objects.filter(
        status=ActivityStatus.active, response_type=ActivityResponseType.public
    )

    dataset = build_dataset()

    sectors_list = []
    total_triggered_activities = 0

    for sector_code, (sector_key, sector_label) in SECTOR_MAP.items():
        sec_activities = active_public_activities.filter(sector=sector_code)
        act_count = sec_activities.count()

        # Dynamically calculate triggered Tinkhundla count
        triggered_admin_ids = set()
        descriptions = []

        for act in sec_activities:
            if act.description:
                descriptions.append(act.description)
            if act.triggers:
                for adm_id, row in dataset.items():
                    if activity_passes(act.triggers, row):
                        triggered_admin_ids.add(adm_id)

        tink_count = len(triggered_admin_ids)
        total_triggered_activities += act_count

        sectors_list.append(
            {
                "key": sector_key,
                "label": sector_label,
                "activities": act_count,
                "tinkhundla": tink_count,
                "description": (
                    " ".join(descriptions)
                    if descriptions
                    else f"Active response interventions for {sector_label}."
                ),
            }
        )

    summary_str = f"{total_triggered_activities} public response activities currently active across Eswatini."  # noqa

    return {
        "lastUpdated": last_updated_str,
        "summary": summary_str,
        "sectors": sectors_list,
        "priorityAreasHref": "/detailed-insights/risk-level",
    }


def get_map_data_config():
    """Service for GET /api/v1/insights/map-data"""
    latest_pub = (
        Publication.objects.filter(status=PublicationStatus.published)
        .order_by("-year_month", "-id")
        .first()
    )

    date_str = (
        latest_pub.year_month.strftime("%Y-%m")
        if latest_pub
        else timezone.now().strftime("%Y-%m")
    )

    # The inventory lives in map_layers so the tab list and the builders that
    # serve those tabs cannot drift apart. `temperature` was renamed to `esi`:
    # the tab shows an ERA5-derived percentile rank, not degrees.
    return {
        "date": date_str,
        "compareTo": None,
        "layers": LAYERS,
        "activeLayer": "drought-class",
    }
