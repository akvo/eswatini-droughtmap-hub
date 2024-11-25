from django.urls import re_path
from . import views
from .views import job_check, create_job

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/health/check",
        views.health_check,
        name="health_check",
    ),
    re_path(r"^(?P<version>(v1))/jobs/create", create_job),
    re_path(r"^(?P<version>(v1))/jobs/check", job_check),
]
