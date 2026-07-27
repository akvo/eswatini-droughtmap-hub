import csv
import io

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.citizen_science import CS_FIELD_KEYS, parse_period
from api.v1.v1_weather.models import (
    AdministrationNormal,
    CitizenScienceReading,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

CS_CSV_COLUMNS = ["administration_id", "year_month", *CS_FIELD_KEYS, "notes"]


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
    list_display = ("station", "date", "parameter", "value", "readings_count")
    list_filter = ("parameter", "station")
    date_hierarchy = "date"


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
