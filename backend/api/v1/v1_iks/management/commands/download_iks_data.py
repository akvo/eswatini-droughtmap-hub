import logging
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


def download_attachment(download_url, save_path):
    """Downloads an attachment from Kobo Toolbox."""
    try:
        response = requests.get(download_url, timeout=30)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Successfully downloaded attachment to {save_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to download attachment {download_url}: {str(e)}")
    return False


class Command(BaseCommand):
    help = "Download and sync IKS data from Kobo Toolbox"

    def handle(self, *args, **options):
        # 1. Load active KoboAdapter
        adapter = KoboAdapter.objects.filter(active=True).first()
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
        for form in forms:
            url = f"{adapter.server_url.rstrip('/')}/api/v2/assets"
            url += f"/{form.uuid}/data/?format=json"
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
                    continue
                data = response.json()
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to fetch data for form {form.uuid}: {str(e)}"
                    )
                )
                continue

            results = data.get("results", [])
            for res in results:
                kobo_id = res.get("_id")
                if not kobo_id:
                    continue

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

                kobo_data, created = KoboData.objects.update_or_create(
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
                    "group_tn4ao32/B1_Which_of_the_fol_vile_endzaweni_yakho",
                    "group_mq8ds86/C1_Which_of_the_fol_lotivile_kulendzawo",
                ]

                # If administration_id was matched, store mapped IKS values
                if administration_id:
                    try:
                        admin_obj = Administration.objects.get(
                            pk=administration_id
                        )
                        for field_name in indicator_fields:
                            answers = res.get(field_name, "")
                            if answers:
                                # Answers is a space separated string
                                # of selected indicators
                                for choice in answers.split():
                                    indicator, _ = (
                                        IKSIndicator.objects.get_or_create(
                                            kobo_form=form, name=choice
                                        )
                                    )
                                    # Create or update Value
                                    IKSValue.objects.update_or_create(
                                        kobo_id=kobo_id,
                                        iks_indicator=indicator,
                                        defaults={
                                            "administration": admin_obj,
                                            "value": "observed",
                                        },
                                    )
                    except Administration.DoesNotExist:
                        logger.warning(
                            f"Administration with ID {administration_id} not found in database."  # noqa
                        )

                # Trigger image download jobs asynchronously
                # if attachments exist
                attachments = res.get("_attachments", [])
                for attach in attachments:
                    download_url = attach.get("download_url")
                    filename = attach.get("filename", "").split("/")[-1]
                    if download_url and filename:
                        # Create async job
                        Jobs.objects.create(
                            type=JobTypes.test,
                            status=JobStatus.pending,
                            info={
                                "filename": filename,
                                "download_url": download_url,
                            },
                        )
                        # Dispatch async task
                        save_path = f"{settings.STORAGE_PATH}/{filename}"
                        async_task(
                            download_attachment,
                            download_url,
                            save_path,
                            group=f"iks-image-{kobo_id}",
                            hook="api.v1.v1_jobs.job.job_done_hook",  # noqa
                        )

                sync_count += 1

        # Update last sync timestamp
        adapter.last_sync_timestamp = timezone.now()
        adapter.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {sync_count} submissions from Kobo Toolbox."
            )
        )
