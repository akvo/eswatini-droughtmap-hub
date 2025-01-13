from pathlib import Path
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema
from django.core.management import call_command
from django.http import HttpResponse
from jsmin import jsmin


@extend_schema(
    description="Get required configuration",
    tags=["Development"]
)
@api_view(["GET"])
def get_config_file(request, version):
    if not Path("source/config/config.min.js").exists():
        call_command("generate_config")
    data = jsmin(open("source/config/config.min.js", "r").read())
    response = HttpResponse(
        data, content_type="application/x-javascript; charset=utf-8"
    )
    return response
