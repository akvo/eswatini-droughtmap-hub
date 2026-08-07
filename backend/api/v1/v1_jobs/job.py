import logging
import os
import rasterio
import geopandas as gpd
import requests
import numpy as np
# from rasterstats import zonal_stats
from rasterio.mask import mask
from time import sleep
from django.core import signing
from django.utils import timezone
from django.conf import settings
from django_q.tasks import async_task
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_jobs.constants import JobStatus, JobTypes
from api.v1.v1_publication.constants import GEONODE_SSL_VERIFY
from api.v1.v1_users.constants import CS_LINK_SALT
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.serializers import (
    ReviewSerializer,
    PublicationSerializer,
)
from api.v1.v1_publication.utils import (
    get_category,
    attach_component_rasters,
    publish_seeded_publication,
)
from utils.email_helper import send_email, EmailTypes

# Set up logging
logger = logging.getLogger(__name__)
tmp_dir = "./tmp"


def demo_q_func(name: str):
    sleep(10)
    return {"name": f"Hello {name}! from Django Queue"}


def demo_q_response_func(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    if task.success:
        job.status = JobStatus.done
        job.available = timezone.now()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def job_done_hook(task):
    # Generic completion hook: mark the linked Job done/failed.
    job = Jobs.objects.filter(task_id=task.id).first()
    if not job:
        logger.warning(f"No Job found for task {task.id}")
        return
    job.attempt = job.attempt + 1
    if task.success:
        job.status = JobStatus.done
        job.available = timezone.now()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def notify_verification_email(email: str, code: str):
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.verification_email,
            context={
                "send_to": [email],
                "verification_code": code,
            },
        )


def notify_reset_password(user: SystemUser, new_user: bool = False):
    if not settings.TEST_ENV:
        email_type = EmailTypes.forgot_password
        if new_user:
            email_type = EmailTypes.new_user_password_setup
        send_email(
            type=email_type,
            context={
                "send_to": [user.email],
                "name": user.name,
                "reset_password_code": user.reset_password_code,
            },
        )


def _cs_link_token(user: SystemUser) -> str:
    return signing.dumps(user.pk, salt=CS_LINK_SALT)


def notify_cs_magic_link(user_id: int):
    """Welcome / fallback sign-in email for a citizen-science observer."""
    user = SystemUser.objects.filter(pk=user_id).first()
    if not user:
        logger.warning(f"notify_cs_magic_link: no user {user_id}")
        return False
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.cs_magic_link,
            context={
                "send_to": [user.email],
                "name": user.name,
                "station_name": user.station_name or "your station",
                "token": _cs_link_token(user),
            },
        )
    return {"email": user.email}


def notify_cs_reminder(user_id: int, month_label: str):
    """Monthly reading reminder for a citizen-science observer."""
    user = SystemUser.objects.filter(pk=user_id).first()
    if not user:
        logger.warning(f"notify_cs_reminder: no user {user_id}")
        return False
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.cs_reminder,
            context={
                "send_to": [user.email],
                "name": user.name,
                "station_name": user.station_name or "your station",
                "month_label": month_label,
                "token": _cs_link_token(user),
            },
        )
    return {"email": user.email, "month": month_label}


def notify_review_completed(
    reviewer_name: str,
    year_month: str,
    publication_id: int,
    review_id: int
):
    if not settings.TEST_ENV:
        admins = SystemUser.objects.filter(
            is_superuser=True
        ).values_list(
            "email", flat=True
        )
        send_email(
            type=EmailTypes.review_completed,
            context={
                "send_to": admins,
                "reviewer_name": reviewer_name,
                "year_month": year_month,
                "id": publication_id,
                "review_id": review_id,
            },
        )


def notify_review_request(
    email: str,
    review_id: int,
    subject: str,
    body: str
):
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.review_request,
            context={
                "send_to": [email],
                "id": review_id,
                "subject": subject,
                "body": body,
            }
        )
    return {
        "email": email,
        "review_id": review_id,
    }


def dispatch_review_request(publication, review, subject, message):
    """Queue one reviewer's invitation email.

    Extracted so a reviewer added to an existing publication gets exactly the
    invitation the original panel got — same placeholders, same Jobs row, same
    async task. A second email path here would drift from this one, and the
    reviewer who received the drifted version is the one least able to notice.
    """
    job = Jobs.objects.create(
        type=JobTypes.review_request,
        status=JobStatus.on_progress,
        result=ReviewSerializer(review).data,
    )
    body = message \
        .replace("{{reviewer_name}}", review.user.name) \
        .replace("{{year_month}}", publication.year_month.strftime("%Y-%m")) \
        .replace("{{due_date}}", publication.due_date.strftime("%Y-%m-%d"))

    job.task_id = async_task(
        "api.v1.v1_jobs.job.notify_review_request",
        review.user.email,
        review.id,
        subject,
        body,
        hook="api.v1.v1_jobs.job.email_notification_results",
    )
    job.save()
    return job


def notify_feedback_received(
    email: str,
    feedback: str
):
    if not settings.TEST_ENV:
        admins = SystemUser.objects.filter(
            is_superuser=True
        ).values_list(
            "email", flat=True
        )
        send_email(
            type=EmailTypes.send_feedback,
            context={
                "send_to": admins,
                "email": email,
                "feedback": feedback,
            }
        )
    return {
        "email": email,
        "feedback": feedback,
    }


def email_notification_results(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    if task.success:
        job.status = JobStatus.done
        job.available = timezone.now()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def download_geonode_dataset(
    download_url: str,
    filename: str,
):
    # Create /tmp directory if it doesn't exist
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    # Download and store it in /tmp directory
    input_file = os.path.join(tmp_dir, filename)
    response = requests.get(download_url, stream=True, verify=GEONODE_SSL_VERIFY)
    if response.status_code == 200:
        with open(input_file, "wb") as f:
            # Write the response in chunks to handle large files
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive new chunks
                    f.write(chunk)
        return input_file
    else:
        logger.error(
            f"Failed to download the file from {download_url}."
            f"Status code: {response.status_code}"
        )
        return False


def download_geonode_dataset_results(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    job_info = job.info
    publication_id = job_info["publication_id"]
    filename = job_info["filename"]
    subject = job_info["subject"]
    message = job_info["message"]

    input_file = os.path.join(tmp_dir, filename)

    if task.success and os.path.exists(input_file):
        job.status = JobStatus.done
        job.available = timezone.now()

        # Create a job
        job = Jobs.objects.create(
            type=JobTypes.initial_cdi_values,
            status=JobStatus.on_progress,
            info={
                "id": publication_id,
                "subject": subject,
                "message": message,
                # Carried across the hop: the seeder sets is_seeder on the
                # DOWNLOAD job, but it is read on the EXTRACTION job by
                # generate_initial_cdi_values_results. Dropping it here left
                # that branch permanently unreachable, which is why
                # publications_seeder had to be run twice before
                # validated_values appeared (design DEMO-1 D-10).
                "is_seeder": job_info.get("is_seeder", False),
            },
        )
        hook = "api.v1.v1_jobs.job.generate_initial_cdi_values_results"
        task_id = async_task(
            "api.v1.v1_jobs.job.generate_initial_cdi_values",
            publication_id,
            input_file,
            hook=hook,
        )
        # Update the job with the task ID
        job.task_id = task_id
        job.save()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def compute_zonal_values(input_file: str) -> list:
    # Indicator-agnostic zonal stats: for each administration polygon, mask
    # the raster to that geometry and reduce the valid, non-negative pixels
    # to a single value via (min + mean) * 0.5. No category here — that is
    # a CDI-specific concept layered on top by callers that need it.
    topojson_file = "./source/eswatini.topojson"
    gdf = gpd.read_file(topojson_file)
    gdf.crs = "epsg:4326"
    results = []
    with rasterio.open(input_file) as src:
        gdf_reprojected = gdf.to_crs(src.crs)
        for _, row in gdf_reprojected.iterrows():
            geom = row["geometry"]
            admin_id = row["administration_id"]
            if geom.is_empty:
                results.append({"administration_id": admin_id, "value": None})
                continue
            try:
                masked_arr, _ = mask(dataset=src, shapes=[geom], crop=True,
                                     nodata=src.nodata, filled=False)
            except ValueError:
                results.append({"administration_id": admin_id, "value": None})
                continue
            masked_arr = masked_arr[0]
            valid_data = masked_arr.compressed()
            if valid_data.size == 0:
                results.append({"administration_id": admin_id, "value": None})
                continue
            positive_values = valid_data[np.where(valid_data >= 0)]
            if positive_values.size == 0:
                results.append({"administration_id": admin_id, "value": None})
                continue
            min_val = np.min(positive_values)
            mean_val = np.mean(positive_values)
            final_value = (min_val + mean_val) * 0.5
            results.append({"administration_id": admin_id, "value": float(final_value)})
    return results


def generate_initial_cdi_values(
    publication_id: int,
    input_file: str,
):
    publication = Publication.objects.filter(
        pk=publication_id
    ).first()
    if not publication:
        logger.error(
            f"Publication with ID {publication_id} does not exist."
        )
        return False

    raw = compute_zonal_values(input_file)
    results = [
        {**item, "category": get_category(item["value"])
                  if item["value"] is not None else None}
        for item in raw
    ]
    publication.initial_values = results
    publication.save()
    return PublicationSerializer(publication).data


def generate_indicator_values(publication_raster_id: int, input_file: str):
    raster = PublicationRaster.objects.filter(pk=publication_raster_id).first()
    if not raster:
        logger.error(f"PublicationRaster {publication_raster_id} does not exist.")
        return False
    raster.values = compute_zonal_values(input_file)
    raster.extracted_at = timezone.now()
    raster.save()
    return {"id": raster.id, "indicator": raster.indicator}


def attach_publication_rasters(publication_id: int):
    # Component discovery walks the GeoNode catalogue up to four times, so it
    # runs here in the worker rather than inline in the create request (D-6):
    # a slow or unreachable GeoNode must never delay or fail publication
    # creation, which only ever needed the CDI raster.
    publication = Publication.objects.filter(pk=publication_id).first()
    if not publication:
        logger.error(f"Publication with ID {publication_id} does not exist.")
        return False
    attached = attach_component_rasters(publication)
    return {"publication": publication_id, "attached": attached}


def download_indicator_dataset_results(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    job_info = job.info
    raster_id = job_info["publication_raster_id"]
    filename = job_info["filename"]
    input_file = os.path.join(tmp_dir, filename)
    if task.success and os.path.exists(input_file):
        job.status = JobStatus.done
        job.available = timezone.now()
        next_job = Jobs.objects.create(
            type=JobTypes.indicator_values,
            status=JobStatus.on_progress,
            info={"publication_raster_id": raster_id},
        )
        task_id = async_task(
            "api.v1.v1_jobs.job.generate_indicator_values",
            raster_id,
            input_file,
            hook="api.v1.v1_jobs.job.generate_indicator_values_results",
        )
        next_job.task_id = task_id
        next_job.save()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def generate_indicator_values_results(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    if task.success:
        job.status = JobStatus.done
        job.available = timezone.now()
    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()


def generate_initial_cdi_values_results(task):
    job = Jobs.objects.get(task_id=task.id)
    job.attempt = job.attempt + 1
    job_info = job.info
    subject = job_info["subject"]
    message = job_info["message"]

    publication = Publication.objects.filter(
        pk=job_info["id"]
    ).first()

    if task.success and publication and len(publication.initial_values):
        job.status = JobStatus.done
        job.available = timezone.now()

        if not subject or not message:
            job.result = task.result
            job.save()

            if job_info.get("is_seeder", False):
                # Seeded publications publish themselves at the end of the
                # extraction chain, so one seeder run is enough. Shared with
                # publications_seeder's repair pass so the two cannot drift.
                publish_seeded_publication(publication)

            # No subject or message provided, so no email to send
            return
        # Send email to all reviewers
        for review in publication.reviews.all():
            dispatch_review_request(publication, review, subject, message)

    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()
