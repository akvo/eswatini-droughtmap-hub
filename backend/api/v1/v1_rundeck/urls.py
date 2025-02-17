from django.urls import re_path
from api.v1.v1_rundeck.views import SettingsViewSet

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/admin/settings",
        SettingsViewSet.as_view({"get": "list", "post": "create"}),
        name="settings",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/setting/(?P<pk>[0-9]+)",
        SettingsViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="settings-details",
    ),
]
