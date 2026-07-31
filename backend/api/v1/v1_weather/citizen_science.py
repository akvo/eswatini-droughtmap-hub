"""Citizen-science helpers (WX-6): period math, completeness, serving
payloads, reminder dispatch and CSV export rows. Kept out of views.py so
each stays small."""
import csv
from datetime import date
from typing import List, Optional

from django.utils import timezone
from django_q.tasks import async_task

from api.v1.v1_jobs.constants import JobStatus, JobTypes
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.constants import (
    CS_AT_RISK_MISSED,
    CS_FIELDS,
    CS_NETWORK,
    CS_REPORTING_WELL_MIN,
    CS_SENSORS,
    CS_WINDOW_MONTHS,
)
from api.v1.v1_weather.models import CitizenScienceReading

CS_FIELD_KEYS = [key for key, _, _ in CS_FIELDS]


def shift_month(value: date, delta: int) -> date:
    total = value.year * 12 + (value.month - 1) + delta
    return date(total // 12, total % 12 + 1, 1)


def parse_period(value: str) -> Optional[date]:
    """'YYYY-MM' -> first-of-month date, or None."""
    try:
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    except (AttributeError, ValueError):
        return None


def period_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def latest_reportable_month(today: Optional[date] = None) -> date:
    """The most recent fully-ended month — what the 1st-of-month email
    asks for, and the last month that counts toward completeness."""
    today = today or timezone.now().date()
    return shift_month(today.replace(day=1), -1)


def trailing_window(today: Optional[date] = None) -> List[date]:
    """The 12 reportable months, newest first (brief §6.2)."""
    end = latest_reportable_month(today)
    return [shift_month(end, -i) for i in range(CS_WINDOW_MONTHS)]


def reading_values(reading: CitizenScienceReading) -> dict:
    return {key: getattr(reading, key) for key in CS_FIELD_KEYS}


def observer_field_keys(user: SystemUser) -> List[str]:
    """Reading fields this observer's station can measure (sensor-gated,
    mockup §6.4). No sensors recorded -> all five (never hide the form)."""
    keys = [
        CS_SENSORS[sensor]
        for sensor in (user.station_sensors or [])
        if CS_SENSORS.get(sensor)
    ]
    return keys or CS_FIELD_KEYS


def active_observers():
    return SystemUser.objects.filter(
        role=UserRoleTypes.observer,
        deleted_at__isnull=True,
        administration__isnull=False,
    ).select_related("administration")


def observer_history(user: SystemUser) -> dict:
    """Observer form payload: station block, 12-month completeness and the
    window's readings (drafts included — it is their own data)."""
    window = trailing_window()
    readings = CitizenScienceReading.objects.filter(
        administration_id=user.administration_id,
        year_month__gte=window[-1],
        year_month__lte=window[0],
    ).order_by("-year_month")
    reported = sum(1 for r in readings if r.submitted_at)
    return {
        "station": {
            "label": user.station_name,
            "administration": user.administration.name,
            "group": user.administration.region,
            "sensors": user.station_sensors,
            "station_type": user.station_type,
        },
        "completeness": {"reported": reported, "of": CS_WINDOW_MONTHS},
        "data": [
            {
                "period": period_label(r.year_month),
                "submitted": r.submitted_at is not None,
                **reading_values(r),
                "notes": r.notes,
            }
            for r in readings
        ],
    }


def admin_network() -> dict:
    """Admin dashboard payload: stats cards + per-station table rows
    (brief §6.3)."""
    window = trailing_window()
    observers = list(active_observers().order_by("station_name"))
    admin_ids = [o.administration_id for o in observers]
    submitted = CitizenScienceReading.objects.filter(
        administration_id__in=admin_ids,
        submitted_at__isnull=False,
    ).values_list("administration_id", "year_month")
    in_window, last_submission = {}, {}
    window_set = set(window)
    for admin_id, year_month in submitted:
        if year_month in window_set:
            in_window.setdefault(admin_id, set()).add(year_month)
        last = last_submission.get(admin_id)
        if not last or year_month > last:
            last_submission[admin_id] = year_month
    rows, reporting_well, at_risk = [], 0, 0
    for observer in observers:
        reported = len(in_window.get(observer.administration_id, set()))
        if reported >= CS_REPORTING_WELL_MIN:
            reporting_well += 1
        if CS_WINDOW_MONTHS - reported >= CS_AT_RISK_MISSED:
            at_risk += 1
        last = last_submission.get(observer.administration_id)
        rows.append(
            {
                "key": observer.administration_id,
                "label": observer.station_name,
                "group": observer.administration.region,
                "sensors": observer.station_sensors,
                "station_type": observer.station_type,
                "observer": {
                    "id": observer.id,
                    "name": observer.name,
                    "email": observer.email,
                },
                "last_submission": period_label(last) if last else None,
                "completeness": {
                    "reported": reported,
                    "of": CS_WINDOW_MONTHS,
                },
            }
        )
    month_start = timezone.now().date().replace(day=1)
    reminders_sent = Jobs.objects.filter(
        type=JobTypes.cs_reminder, created__gte=month_start
    ).count()
    return {
        "stats": {
            "stations": len(observers),
            "reporting_well": reporting_well,
            "at_risk": at_risk,
            "reminders_sent_this_month": reminders_sent,
        },
        "data": rows,
    }


def serving_payload(
    administration, period: date, history: int = 0
) -> dict:
    """Review-page CS block (WX-6 §4): exact-match per Inkhundla, submitted
    readings only, explicit no-data otherwise. Optional trailing history
    (D-10) — absent months are absent, never fabricated."""
    payload = {
        "key": administration.id,
        "label": administration.name,
        "group": administration.region,
    }
    reading = CitizenScienceReading.objects.filter(
        administration=administration,
        year_month=period,
        submitted_at__isnull=False,
    ).first()
    if reading:
        observer = active_observers().filter(
            administration=administration
        ).first()
        payload["data"] = [
            {
                "key": key,
                "label": label,
                "value": getattr(reading, key),
                "units": units,
            }
            for key, label, units in CS_FIELDS
        ]
        payload["meta"] = {
            "network": CS_NETWORK,
            "station": observer.station_name if observer else None,
            "period": period_label(period),
            "notes": reading.notes or None,
        }
    else:
        payload["data"] = None
        payload["meta"] = {"reason": "no_citizen_science_for_period"}
    if history:
        rows = CitizenScienceReading.objects.filter(
            administration=administration,
            submitted_at__isnull=False,
            year_month__gte=shift_month(period, -(history - 1)),
            year_month__lte=period,
        ).order_by("year_month")
        payload["history"] = [
            {"period": period_label(r.year_month), **reading_values(r)}
            for r in rows
        ]
    return payload


def dispatch_cs_magic_link(user: SystemUser) -> Jobs:
    """Queue one sign-in/welcome magic-link email. Single path for the
    fallback sign-in endpoint, the Django-admin observer creation and the
    stations POST — so the three can never drift apart."""
    job = Jobs.objects.create(
        type=JobTypes.cs_magic_link,
        status=JobStatus.on_progress,
        result=user.email,
    )
    job.task_id = async_task(
        "api.v1.v1_jobs.job.notify_cs_magic_link",
        user.id,
        hook="api.v1.v1_jobs.job.email_notification_results",
    )
    job.save()
    return job


def dispatch_cs_reminders(user_ids=None) -> int:
    """Queue one reminder email per targeted observer. No ids = every
    active observer still missing last month's reading (all-due); with ids
    = the admin's row-level nudge. Same path for cron and the API (D-8)."""
    period = latest_reportable_month()
    month_label = period.strftime("%B %Y")
    observers = active_observers()
    if user_ids:
        observers = observers.filter(pk__in=user_ids)
    else:
        submitted_ids = CitizenScienceReading.objects.filter(
            year_month=period, submitted_at__isnull=False
        ).values_list("administration_id", flat=True)
        observers = observers.exclude(administration_id__in=submitted_ids)
    count = 0
    for observer in observers:
        job = Jobs.objects.create(
            type=JobTypes.cs_reminder,
            status=JobStatus.on_progress,
            result=observer.email,
        )
        job.task_id = async_task(
            "api.v1.v1_jobs.job.notify_cs_reminder",
            observer.id,
            month_label,
            hook="api.v1.v1_jobs.job.email_notification_results",
        )
        job.save()
        count += 1
    return count


EXPORT_COLUMNS = [
    "administration_id",
    "inkhundla",
    "region",
    "station",
    "year_month",
    *CS_FIELD_KEYS,
    "notes",
    "submitted_at",
]


def write_export_csv(target) -> None:
    """Write every reading (drafts included, flagged by empty submitted_at)
    to a file-like target."""
    stations = {
        o.administration_id: o.station_name for o in active_observers()
    }
    writer = csv.writer(target)
    writer.writerow(EXPORT_COLUMNS)
    readings = CitizenScienceReading.objects.select_related(
        "administration"
    ).order_by("administration__name", "year_month")
    for r in readings:
        writer.writerow(
            [
                r.administration_id,
                r.administration.name,
                r.administration.region,
                stations.get(r.administration_id, ""),
                period_label(r.year_month),
                *[getattr(r, key) for key in CS_FIELD_KEYS],
                r.notes,
                r.submitted_at.isoformat() if r.submitted_at else "",
            ]
        )
