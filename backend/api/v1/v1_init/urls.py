from django.urls import re_path
from api.v1.v1_init.views import (
    health_check,
    SecretKeyView,
    TSContactView,
    AdminContactView,
    SettingsView,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/health/check",
        health_check,
        name="health_check",
    ),
    re_path(
        r"^(?P<version>(v1))/settings/secret-key",
        SecretKeyView.as_view(),
        name="secret_key",
    ),
    re_path(
        r"^(?P<version>(v1))/settings",
        SettingsView.as_view(),
        name="settings",
    ),
    re_path(
        r"^(?P<version>(v1))/contacts/ts",
        TSContactView.as_view(),
        name="contacts_ts",
    ),
    re_path(
        r"^(?P<version>(v1))/contacts/dha",
        AdminContactView.as_view(),
        name="contacts_admin",
    ),
]
