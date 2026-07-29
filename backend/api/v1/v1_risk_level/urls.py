from django.urls import re_path
from api.v1.v1_risk_level.views import RiskLevelsView

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/risk-levels$",
        RiskLevelsView.as_view(),
        name="risk-levels-list",
    ),
]
