from django.urls import re_path
from api.v1.v1_risk_level.views import RiskLevelDetailView, RiskLevelsView

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/risk-levels$",
        RiskLevelsView.as_view(),
        name="risk-levels-list",
    ),
    re_path(
        r"^(?P<version>(v1))/risk-levels/(?P<administration_id>[0-9]+)$",
        RiskLevelDetailView.as_view(),
        name="risk-levels-detail",
    ),
]
