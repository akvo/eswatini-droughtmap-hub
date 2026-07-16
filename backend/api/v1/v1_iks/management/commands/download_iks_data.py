import json
import logging
from datetime import timezone as dt_timezone
from urllib.parse import quote

import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from shapely.geometry import Point
import geopandas as gpd

from api.v1.v1_iks.models import (
    KoboAdapter,
    KoboForm,
    KoboData,
    IKSIndicator,
    IKSValue,
)
from api.v1.v1_publication.models import Administration
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_jobs.constants import JobStatus, JobTypes
from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def download_attachment(download_url, save_path, username=None, password=None):
    """Downloads an attachment from Kobo Toolbox."""
    try:
        auth = (username, password) if username and password else None
        response = requests.get(download_url, auth=auth, timeout=30)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Successfully downloaded attachment to {save_path}")
            return True
        else:
            logger.error(
                f"Kobo status {response.status_code} for {download_url}"
            )
    except Exception as e:
        logger.error(f"Failed attachment {download_url}: {str(e)}")
    return False


class Command(BaseCommand):
    help = "Download and sync IKS data from Kobo Toolbox"

    def handle(self, *args, **options):
        # 1. Load active KoboAdapter
        adapter = (
            KoboAdapter.objects.filter(active=True)
            .order_by("-updated_at")
            .first()
        )
        if not adapter:
            self.stdout.write(
                self.style.WARNING("No active KoboAdapter found.")
            )
            return

        # 2. Load all forms
        forms = KoboForm.objects.all()
        if not forms.exists():
            self.stdout.write(self.style.WARNING("No KoboForm registered."))
            return

        # Load TopoJSON using geopandas
        topojson_path = "./source/eswatini.topojson"
        try:
            gdf = gpd.read_file(topojson_path)
            if gdf.crs is None:
                gdf.set_crs("EPSG:4326", inplace=True)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to load topojson: {str(e)}")
            )
            return

        headers = {}
        # Support API Token if available, otherwise fallback to Basic Auth
        # In a real setup, we would request/authenticate with Kobo API
        auth = (adapter.username, adapter.password)

        sync_count = 0
        # Track the newest submission actually processed so the next run
        # only pulls records after it (incremental sync).
        newest = adapter.last_sync_timestamp
        for form in forms:
            url = self._build_data_url(adapter, form)

            # Kobo paginates at 100 records per page; follow the "next"
            # link until it is null. Pages are processed and dropped as we
            # go so memory stays flat regardless of total submission count.
            while url:
                try:
                    response = requests.get(
                        url, auth=auth, headers=headers, timeout=30
                    )
                    if response.status_code != 200:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Kobo API returned status {response.status_code} for form {form.uuid}"  # noqa
                            )
                        )
                        break
                    data = response.json()
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to fetch data for form {form.uuid}: {str(e)}"  # noqa
                        )
                    )
                    break

                for res in data.get("results", []):
                    sub_time = self._process_submission(
                        adapter, form, res, gdf
                    )
                    if sub_time is None:
                        continue
                    sync_count += 1
                    if newest is None or sub_time > newest:
                        newest = sub_time

                url = data.get("next")

        # Advance the cursor to the newest submission seen (its own clock),
        # which is safer than wall-clock now() against API/DB skew.
        adapter.last_sync_timestamp = newest or timezone.now()
        adapter.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {sync_count} submissions from Kobo Toolbox."
            )
        )

    def _build_data_url(self, adapter, form):
        """Build the Kobo data URL, filtering to new submissions when
        the adapter has a last_sync_timestamp."""
        url = f"{adapter.server_url.rstrip('/')}/api/v2/assets"
        url += f"/{form.uuid}/data/?format=json"
        if adapter.last_sync_timestamp:
            # ponytail: Kobo _submission_time is UTC; format the cursor in
            # UTC so the $gt comparison lines up.
            cursor = adapter.last_sync_timestamp.astimezone(
                dt_timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S")
            query = {"_submission_time": {"$gt": cursor}}
            url += "&query=" + quote(json.dumps(query))
        return url

    def _process_submission(self, adapter, form, res, gdf):
        """Upsert a single Kobo submission and its IKS values.

        Returns the submission_time on success, or None if skipped.
        """
        kobo_id = res.get("_id")
        if not kobo_id:
            return None

        # Parse geolocation
        gps_str = res.get("survey_start_gps", "")
        lat, lon = None, None
        administration_id = None
        if gps_str:
            try:
                parts = gps_str.split()
                if len(parts) >= 2:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    # Point in polygon check
                    point = Point(lon, lat)
                    matched = gdf[gdf.geometry.contains(point)]
                    if not matched.empty:
                        administration_id = matched.iloc[0][
                            "administration_id"
                        ]
            except Exception as ex:
                logger.error(f"Error parsing GPS {gps_str}: {str(ex)}")

        # Get or create KoboData
        sub_time_str = res.get("_submission_time", "")
        sub_time = timezone.now()
        if sub_time_str:
            parsed = parse_datetime(sub_time_str)
            if parsed:
                sub_time = (
                    timezone.make_aware(parsed)
                    if timezone.is_naive(parsed)
                    else parsed
                )

        KoboData.objects.update_or_create(
            kobo_id=kobo_id,
            defaults={
                "form": form,
                "geo": (
                    {"latitude": lat, "longitude": lon}
                    if lat and lon
                    else None
                ),
                "submission_time": sub_time,
                "submitted_by": res.get("_submitted_by"),
                "instance_name": res.get("meta/instanceID"),
                "raw_data": res,
            },
        )

        # Map Indicators and values
        # Scan common indicator group keys B1 and C1
        indicator_fields = [
            (
                "group_tn4ao32/B1_Which_of_the_fol_vile_endzaweni_yakho",
                "B",
            ),
            (
                "group_mq8ds86/C1_Which_of_the_fol_lotivile_kulendzawo",
                "C",
            ),
        ]

        # If administration_id was matched, store mapped IKS values
        if administration_id:
            try:
                admin_obj = Administration.objects.get(pk=administration_id)
                for field_name, section in indicator_fields:
                    answers = res.get(field_name, "")
                    if answers:
                        # Answers is a space separated string
                        # of selected indicators
                        for choice in answers.split():
                            indicator, created = (
                                IKSIndicator.objects.get_or_create(
                                    kobo_form=form,
                                    name=choice,
                                    defaults={"section": section},
                                )
                            )
                            # Backfill section on pre-existing rows
                            if not created and not indicator.section:
                                indicator.section = section
                                indicator.save(update_fields=["section"])
                            # Create or update Value
                            IKSValue.objects.update_or_create(
                                kobo_id=kobo_id,
                                iks_indicator=indicator,
                                defaults={
                                    "administration": admin_obj,
                                    "value": "observed",
                                },
                            )

                # Process Section D1: Soil moisture
                soil_field = (
                    "group_bx6rt12/D1_How_is_the_soil_atsi_endzaweni_yakho"
                )
                soil_val = res.get(soil_field)
                if soil_val:
                    indicator, _ = IKSIndicator.objects.get_or_create(
                        kobo_form=form,
                        name="soil_moisture",
                        defaults={"section": "D"},
                    )
                    IKSValue.objects.update_or_create(
                        kobo_id=kobo_id,
                        iks_indicator=indicator,
                        defaults={
                            "administration": admin_obj,
                            "value": soil_val,
                        },
                    )

                # Process Section D2: Vegetation greenness
                veg_field = (
                    "group_bx6rt12/D2_How_is_the_veget_ato_endzaweni_yakho"
                )
                veg_val = res.get(veg_field)
                if veg_val:
                    indicator, _ = IKSIndicator.objects.get_or_create(
                        kobo_form=form,
                        name="vegetation_greenness",
                        defaults={"section": "D"},
                    )
                    IKSValue.objects.update_or_create(
                        kobo_id=kobo_id,
                        iks_indicator=indicator,
                        defaults={
                            "administration": admin_obj,
                            "value": veg_val,
                        },
                    )

            except Administration.DoesNotExist:
                logger.warning(
                    f"Administration with ID {administration_id} not found in database."  # noqa
                )

        # Trigger image download jobs asynchronously if attachments exist
        attachments = res.get("_attachments", [])
        for attach in attachments:
            download_url = attach.get("download_url")
            filename = attach.get("filename", "").split("/")[-1]
            if download_url and filename:
                # Create async job
                job = Jobs.objects.create(
                    type=JobTypes.test,
                    status=JobStatus.pending,
                    info={
                        "filename": filename,
                        "download_url": download_url,
                    },
                )
                # Dispatch async task and link its task_id so the
                # completion hook can resolve this Job.
                save_path = f"{settings.STORAGE_PATH}/{filename}"
                task_id = async_task(
                    download_attachment,
                    download_url,
                    save_path,
                    username=adapter.username,
                    password=adapter.password,
                    group=f"iks-image-{kobo_id}",
                    hook="api.v1.v1_jobs.job.job_done_hook",  # noqa
                )
                job.task_id = task_id
                job.save()

        return sub_time
