from django.urls import re_path
from . import views

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/health/check",
        views.health_check,
        name="health_check",
    ),
    re_path(
        r"^(?P<version>(v1))/dummy/reviewer-only",
        views.reviewer_only,
        name="reviewer_only",
    ),
    re_path(
        r"^(?P<version>(v1))/dummy/admin-only",
        views.admin_only,
        name="admin_only",
    ),
]
