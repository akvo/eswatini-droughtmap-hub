from django.urls import re_path
from .views import view_job, create_job

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/jobs/create$",
        create_job,
        name="create_job"
    ),
    re_path(
        r"^(?P<version>(v1))/job/(?P<job_id>[0-9]+)$",
        view_job,
        name="view_job"
    ),
]
