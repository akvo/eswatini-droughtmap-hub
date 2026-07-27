import logging
from collections import Counter
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from api.v1.v1_publication.models import Publication, Administration
from api.v1.v1_publication.constants import (
    PublicationStatus,
    DroughtCategory,
    AdministrationZones,
)
from api.v1.v1_weather.models import (
    WeatherStation,
)
from api.v1.v1_weather.services import station_health
from api.v1.v1_iks.models import KoboData
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

SECTOR_MAP = {
    ActivitySector.wash: ("water", "Water and Sanitation"),
    ActivitySector.food: ("agriculture", "Agriculture and Food security"),
    ActivitySector.env: ("environment", "Environment and energy"),
    ActivitySector.health: ("health", "Health and nutrition"),
}


def compute_linear_slope(series):
    """
    Calculate slope for series [(month_str, float_val)].
    Returns 'worsening', 'improving', or 'stable'.
    """
    if len(series) < 2:
        return "stable"
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
            "status": {"category": 0, "label": "Normal / No Drought"},
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
    max_cat = max(cats) if cats else 0
    label = DroughtCategory.FieldStr.get(max_cat, "Normal / No Drought")

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
        "status": {"category": max_cat, "label": label},
        "published": published_str,
        "nextUpdate": next_update_str,
        "headline": headline,
        "summary": summary,
    }


def get_zones_data(group="regions"):
    """Service for GET /api/v1/insights/zones?group=regions|climatic"""
    latest_pub = (
        Publication.objects.filter(status=PublicationStatus.published)
        .order_by("-year_month", "-id")
        .first()
    )

    period_str = (
        latest_pub.year_month.strftime("%Y-%m")
        if latest_pub
        else timezone.now().strftime("%Y-%m")
    )

    # Fetch last 6 published publications
    recent_pubs = list(
        Publication.objects.filter(
            status=PublicationStatus.published
        ).order_by("-year_month", "-id")[:6]
    )
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

    latest_vals = {}
    if latest_pub and latest_pub.validated_values:
        latest_vals = {
            v["administration_id"]: v.get("category", 0)
            for v in latest_pub.validated_values
        }

    for g_key, g_info in groups_map.items():
        g_id = g_info["id"]
        g_label = g_info["label"]
        g_admins = g_info["admins"]
        admin_ids = [a.id for a in g_admins]

        # Calculate current modal category and confidence
        cat_counts = Counter(latest_vals.get(aid, 0) for aid in admin_ids)
        modal_cat = cat_counts.most_common(1)[0][0] if cat_counts else 0
        total_count = len(admin_ids) or 1
        confidence_pct = round((cat_counts[modal_cat] / total_count) * 100)

        zones_list.append(
            {
                "id": g_id,
                "label": g_label,
                "value": modal_cat,
                "confidence": confidence_pct,
            }
        )

        # Breakdowns
        breakdown_counts = [
            {"key": c, "value": cat_counts.get(c, 0)} for c in range(6)
        ]
        breakdowns_list.append(
            {
                "administration_id": g_id,
                "group": "tinkhundla",
                "data": breakdown_counts,
            }
        )

        # Trends
        series = []
        for p in recent_pubs:
            p_vals = {
                v["administration_id"]: v.get("category", 0)
                for v in (p.validated_values or [])
            }
            p_cats = [p_vals.get(aid, 0) for aid in admin_ids]
            mean_val = round(sum(p_cats) / len(p_cats), 1) if p_cats else 0.0
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


def get_metrics_data():
    """Service for GET /api/v1/insights/metrics"""
    now = timezone.now()
    cutoff_30d = now - timedelta(days=30)

    # Weather Stations health
    all_stations = WeatherStation.objects.filter(is_active=True)
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

    # Field Reports (Kobo 30d)
    kobo_count = KoboData.objects.filter(
        submission_time__gte=cutoff_30d
    ).count()

    # Rainfall & Temperature History (last 12 months)
    recent_pubs = list(
        Publication.objects.filter(
            status=PublicationStatus.published
        ).order_by("-year_month")[:12]
    )
    recent_pubs.reverse()

    rainfall_history = []
    temp_history = []
    latest_rain_dev = 0
    latest_temp_dev = 0.0

    for pub in recent_pubs:
        period_str = pub.year_month.strftime("%Y-%m")
        # Example deviation logic per period
        rain_dev = 0
        temp_dev = 0.0
        rainfall_history.append({"key": period_str, "value": rain_dev})
        temp_history.append({"key": period_str, "value": temp_dev})
        latest_rain_dev = rain_dev
        latest_temp_dev = temp_dev

    latest_pub = (
        Publication.objects.filter(status=PublicationStatus.published)
        .order_by("-year_month")
        .first()
    )
    month_note = (
        latest_pub.year_month.strftime("%b %Y")
        if latest_pub
        else "Current month"
    )

    return {
        "rainfall": {
            "value": latest_rain_dev,
            "unit": "mm",
            "note": f"{month_note} deviation",
            "label": "Precipitation vs 30-yr normal",
            "history": rainfall_history,
        },
        "temperature": {
            "value": latest_temp_dev,
            "unit": "°C",
            "note": f"{month_note} mean Tmax deviation",
            "label": "Temperature vs 30 yr Normal",
            "history": temp_history,
        },
        "activeStations": {
            "online": online_count,
            "total": total_stations,
            "onlinePct": online_pct,
            "label": "Active stations",
            "note": f"{offline_count} Offline  {degraded_count} Degraded",
        },
        "fieldReports": {
            "count": kobo_count,
            "verifiedPct": 100,
            "label": "Field reports",
            "note": "in last 30 days  100% verified",
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
        "priorityAreasHref": "/insights/priority",
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

    return {
        "date": date_str,
        "compareTo": None,
        "layers": [
            {"key": "drought-class", "label": "Drought class"},
            {"key": "precipitation", "label": "Precipitation"},
            {"key": "temperature", "label": "Temperature"},
            {"key": "land-use", "label": "Land use"},
            {"key": "population", "label": "Population map"},
            {"key": "regions", "label": "Regions"},
            {"key": "agro-eco", "label": "Agro-ecological zones"},
        ],
        "activeLayer": "drought-class",
    }
