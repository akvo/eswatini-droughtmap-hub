from django.urls import re_path
from . import views
from .views import get_config_file

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/health/check",
        views.health_check,
        name="health_check",
    ),
    re_path(r"^(?P<version>(v1))/config.js", get_config_file),
]
