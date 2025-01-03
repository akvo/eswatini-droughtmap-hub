from pathlib import Path

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.core.management import call_command
from django.http import HttpResponse
from jsmin import jsmin


@extend_schema(description="Use to check System health", tags=["Dev"])
@api_view(["GET"])
def health_check(request, version):
    return Response({"message": "OK"}, status=status.HTTP_200_OK)


@extend_schema(description="Get required configuration", tags=["Dev"])
@api_view(["GET"])
def get_config_file(request, version):
    if not Path("source/config/config.min.js").exists():
        call_command("generate_config")
    data = jsmin(open("source/config/config.min.js", "r").read())
    response = HttpResponse(
        data, content_type="application/x-javascript; charset=utf-8"
    )
    return response
