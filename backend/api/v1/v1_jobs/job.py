import logging
import os
import rasterio
import geopandas as gpd
import requests
from rasterstats import zonal_stats
from time import sleep
from django.utils import timezone
from django.conf import settings
from django_q.tasks import async_task
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_jobs.constants import JobStatus, JobTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.serializers import (
    ReviewSerializer,
    PublicationSerializer,
)
from api.v1.v1_publication.utils import get_category
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
    response = requests.get(download_url, stream=True)
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


def generate_initial_cdi_values(
    publication_id: int,
    input_file: str,
):
    publication = Publication.objects.filter(
        pk=publication_id
    ).first()
    # Read the topojson file to load all Administrations
    topojson_file = "./source/eswatini.topojson"
    gdf = gpd.read_file(topojson_file)

    gdf.crs = "epsg:4326"

    # Ensure the CRS of the GeoDataFrame and the raster are the same
    with rasterio.open(input_file) as src:
        gdf = gdf.to_crs(src.crs)

    # Perform zonal statistics
    zs = zonal_stats(
        gdf,
        input_file,
        stats=["median"],  # Specify the statistics you need
        geojson_out=True  # Output as GeoJSON features for easier handling
    )
    # Map the zonal statistics to a new column in the GeoDataFrame
    gdf["raster_values"] = [feat["properties"] for feat in zs]

    # Convert raster_values to separate columns for easier analysis
    gdf["value"] = gdf["raster_values"].apply(
        lambda x: x.get("median", None)
    )
    # Add a new column 'category' using the get_category function
    gdf["category"] = gdf["value"].apply(get_category)

    # Remove the original 'raster_values' column if not needed
    gdf = gdf.drop(columns=["raster_values"])

    # Now you have columns like 'value' in your GeoDataFrame
    result = gdf[["administration_id", "value", "category"]]

    publication.initial_values = result.to_dict(orient="records")
    publication.save()
    return PublicationSerializer(publication).data


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

        for review in publication.reviews.all():
            # Create a job
            job = Jobs.objects.create(
                type=JobTypes.review_request,
                status=JobStatus.on_progress,
                result=ReviewSerializer(review).data,
            )
            # Replace placeholders in the message
            body = message \
                .replace(
                    "{{reviewer_name}}",
                    review.user.name
                ) \
                .replace(
                    "{{year_month}}",
                    publication.year_month.strftime("%Y-%m")
                ) \
                .replace(
                    "{{due_date}}",
                    publication.due_date.strftime("%Y-%m-%d")
                )

            # Dispatch the send email job for each reviewer
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_review_request",
                review.user.email,
                review.id,
                subject,
                body,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            # Update the job with the task ID
            job.task_id = task_id
            job.save()

    else:
        job.status = JobStatus.failed
    job.result = task.result
    job.save()
