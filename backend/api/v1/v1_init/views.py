from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_q.tasks import async_task, result


@extend_schema(description="Use to check System health", tags=["Dev"])
@api_view(["GET"])
def health_check(request, version):
    return Response({"message": "OK"}, status=status.HTTP_200_OK)


@extend_schema(
    description="To get the result of job",
    tags=["Job"],
    parameters=[
        OpenApiParameter(
            name="task_id",
            required=False,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
@api_view(["GET"])
def job_check(request, version):
    r = result(request.GET.get("task_id"))
    if r:
        return Response({"message": r}, status=status.HTTP_200_OK)
    return Response(
        {"message": "Job is in-progress"},
        status=status.HTTP_200_OK
    )


@extend_schema(
    description="To create new job",
    tags=["Job"],
    parameters=[
        OpenApiParameter(
            name="name",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
@api_view(["GET"])
def create_job(request, version):
    name = request.GET.get("name")
    task_id = async_task(
        "utils.functions.demo_q_func",
        name,
        hook="utils.functions.demo_q_response_func",
    )
    return Response({"task_id": task_id}, status=status.HTTP_200_OK)
