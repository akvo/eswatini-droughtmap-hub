import csv
import io
from datetime import date

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.citizen_science import CS_FIELD_KEYS, parse_period
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    AdministrationNormal,
    CitizenScienceReading,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

CS_CSV_COLUMNS = ["administration_id", "year_month", *CS_FIELD_KEYS, "notes"]

# SwaziMet historical station records (WX-11 D-13). Same layout as
# eswatini-v2/data/station_history/swazimet_station_history_template.csv —
# the partner fills that template, an admin uploads it here.
STATION_HISTORY_COLUMNS = [
    "wigos_id",
    "station_name",
    "date",
    "parameter",
    "value",
    "readings_count",
]
STATION_HISTORY_PARAMETERS = (
    WeatherParameter.precipitation,
    WeatherParameter.tmax,
    WeatherParameter.tmin,
    WeatherParameter.tmean,
)
STATION_HISTORY_EXAMPLE_ROWS = [
    ["0-20000-0-68391", "MBABANE", "2023-01-01", "precipitation", "0.0", "1"],
    ["0-20000-0-68391", "MBABANE", "2023-01-01", "tmax", "27.4", "1"],
    ["0-20000-0-68391", "MBABANE", "2023-01-01", "tmin", "16.2", "1"],
    ["0-20000-0-68391", "MBABANE", "2023-01-02", "precipitation", "", ""],
]


def parse_station_history(reader, stations: dict) -> tuple:
    """CSV rows -> (StationDailyAggregate objects, errors, skipped_empty).

    `stations` maps both the WIGOS id and the upper-cased name to a station.
    An empty value is a missing day and is skipped — never written as 0,
    because a 0 is a dry day and enters the rainfall total.
    """
    rows, errors, skipped_empty = [], [], 0
    for line, row in enumerate(reader, start=2):
        wigos = (row.get("wigos_id") or "").strip()
        name = (row.get("station_name") or "").strip().upper()
        station = stations.get(wigos) or stations.get(name)
        if station is None:
            errors.append(f"row {line}: unknown station {wigos or name!r}")
            continue
        parameter = (row.get("parameter") or "").strip().lower()
        if parameter not in STATION_HISTORY_PARAMETERS:
            errors.append(f"row {line}: parameter {parameter!r} not allowed")
            continue
        try:
            day = date.fromisoformat((row.get("date") or "").strip())
        except ValueError:
            errors.append(f"row {line}: date is not YYYY-MM-DD")
            continue
        raw = (row.get("value") or "").strip()
        if not raw:
            skipped_empty += 1
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"row {line}: value {raw!r} is not a number")
            continue
        if parameter == WeatherParameter.precipitation and value < 0:
            errors.append(f"row {line}: negative rainfall")
            continue
        raw_count = (row.get("readings_count") or "").strip()
        count = int(raw_count) if raw_count.isdigit() else 1
        rows.append(
            StationDailyAggregate(
                station=station,
                date=day,
                parameter=parameter,
                value=value,
                readings_count=count,
                # A daily-summary source: one reading is the whole day.
                expected_count=count,
                is_seeded=False,
            )
        )
    return rows, errors, skipped_empty


@admin.register(WeatherSource)
class WeatherSourceAdmin(admin.ModelAdmin):
    list_display = ("base_url", "collection_id", "is_active", "updated_at")


@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):
    list_display = (
        "wigos_id",
        "name",
        "region",
        "metadata_status",
        "is_active",
        "last_synced_at",
    )
    search_fields = ("wigos_id", "name")
    list_filter = ("region", "is_active")


@admin.register(StationDailyAggregate)
class StationDailyAggregateAdmin(admin.ModelAdmin):
    """Daily station values, plus the SwaziMet history import (WX-11 D-13):
    download the template, have SwaziMet fill it, upload. Days already in
    the table — ingested from WIS2 or imported before — are kept, so a
    re-upload never rewrites live data; delete the rows first to replace
    them."""

    change_list_template = (
        "admin/v1_weather/stationdailyaggregate/change_list.html"
    )
    list_display = ("station", "date", "parameter", "value", "readings_count")
    list_filter = ("parameter", "station", "is_seeded")
    date_hierarchy = "date"

    def get_urls(self):
        return [
            path(
                "csv-template/",
                self.admin_site.admin_view(self.csv_template_view),
                name="station_history_csv_template",
            ),
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="station_history_import_csv",
            ),
        ] + super().get_urls()

    def csv_template_view(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            "attachment; filename=swazimet_station_history_template.csv"
        )
        writer = csv.writer(response)
        writer.writerow(STATION_HISTORY_COLUMNS)
        writer.writerows(STATION_HISTORY_EXAMPLE_ROWS)
        return response

    def import_csv_view(self, request):
        stations = {
            s.wigos_id: s for s in WeatherStation.objects.all()
        }
        stations.update(
            {s.name.upper(): s for s in WeatherStation.objects.all()}
        )
        if request.method != "POST" or not request.FILES.get("csv_file"):
            return render(
                request,
                "admin/station_history_import.html",
                {
                    **self.admin_site.each_context(request),
                    "stations": sorted(
                        {s.wigos_id: s for s in stations.values()}.values(),
                        key=lambda s: s.name,
                    ),
                },
            )
        decoded = request.FILES["csv_file"].read().decode("utf-8-sig")
        rows, errors, skipped_empty = parse_station_history(
            csv.DictReader(io.StringIO(decoded)), stations
        )
        # ponytail: ignore_conflicts is the whole "existing days win" rule —
        # the unique (station, date, parameter) key rejects duplicates and
        # PostgreSQL does it in one statement. Created = count delta.
        before = StationDailyAggregate.objects.count()
        StationDailyAggregate.objects.bulk_create(
            rows, batch_size=2000, ignore_conflicts=True
        )
        created = StationDailyAggregate.objects.count() - before
        kept = len(rows) - created
        summary = (
            f"Imported {created} station-days; {kept} already present "
            f"(kept); {skipped_empty} empty values skipped."
        )
        level = messages.SUCCESS
        if errors:
            level = messages.WARNING
            summary += f" {len(errors)} rows rejected: " + "; ".join(
                errors[:10]
            )
        self.message_user(request, summary, level=level)
        return redirect("..")


@admin.register(CitizenScienceReading)
class CitizenScienceReadingAdmin(admin.ModelAdmin):
    """Readings admin with the CSV backfill path (WX-6 D-9): download the
    template, fill historical months, import — rows upsert on
    (administration, year_month) and are stamped submitted."""

    change_list_template = (
        "admin/v1_weather/citizensciencereading/change_list.html"
    )
    list_display = (
        "administration",
        "year_month",
        "min_temperature",
        "max_temperature",
        "precipitation",
        "soil_moisture",
        "soil_temperature",
        "submitted_at",
    )
    list_filter = ("administration__region",)
    search_fields = ("administration__name",)
    date_hierarchy = "year_month"

    def get_urls(self):
        return [
            path(
                "csv-template/",
                self.admin_site.admin_view(self.csv_template_view),
                name="cs_reading_csv_template",
            ),
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="cs_reading_import_csv",
            ),
        ] + super().get_urls()

    def csv_template_view(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            "attachment; filename=citizen_science_template.csv"
        )
        writer = csv.writer(response)
        writer.writerow(CS_CSV_COLUMNS)
        writer.writerow([4588078, "2026-05", 12.1, 28.4, 55, "", 17.4, ""])
        return response

    def import_csv_view(self, request):
        if request.method != "POST" or not request.FILES.get("csv_file"):
            return render(
                request,
                "admin/cs_csv_import.html",
                {**self.admin_site.each_context(request)},
            )
        decoded = request.FILES["csv_file"].read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        created = updated = 0
        errors = []
        for line, row in enumerate(reader, start=2):
            period = parse_period((row.get("year_month") or "").strip())
            administration = Administration.objects.filter(
                pk=(row.get("administration_id") or "").strip() or None
            ).first()
            if not period or not administration:
                errors.append(f"row {line}: bad administration_id/year_month")
                continue
            defaults = {"notes": row.get("notes") or ""}
            bad_value = False
            for key in CS_FIELD_KEYS:
                raw = (row.get(key) or "").strip()
                try:
                    defaults[key] = float(raw) if raw else None
                except ValueError:
                    errors.append(f"row {line}: {key} is not a number")
                    bad_value = True
                    break
            if bad_value:
                continue
            defaults["submitted_at"] = timezone.now()
            _, was_created = CitizenScienceReading.objects.update_or_create(
                administration=administration,
                year_month=period,
                defaults=defaults,
            )
            created, updated = (
                (created + 1, updated)
                if was_created
                else (created, updated + 1)
            )
        level = messages.WARNING if errors else messages.SUCCESS
        summary = f"Imported: {created} created, {updated} updated."
        if errors:
            summary += " Skipped " + "; ".join(errors[:10])
        self.message_user(request, summary, level=level)
        return redirect("..")


@admin.register(AdministrationNormal)
class AdministrationNormalAdmin(admin.ModelAdmin):
    list_display = (
        "administration",
        "month",
        "parameter",
        "value",
        "dataset",
        "pixel_count",
    )
    list_filter = ("parameter", "month", "dataset")
    search_fields = ("administration__name",)
