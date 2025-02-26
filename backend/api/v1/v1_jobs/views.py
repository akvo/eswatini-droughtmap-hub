from rest_framework import status, serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from django_q.tasks import async_task
from .models import Jobs
from .constants import JobTypes, JobStatus
from .serializers import JobSerializer, CreateJobSerializer


@extend_schema(
    description="To get the result of job",
    tags=["Jobs"],
    responses=JobSerializer,
)
@api_view(["GET"])
def view_job(request, job_id, version):
    job = get_object_or_404(Jobs, pk=job_id)
    serializer = JobSerializer(
        instance=job
    )
    return Response(
        data=serializer.data,
        status=status.HTTP_200_OK
    )


@extend_schema(
    description="To create new job",
    tags=["Jobs"],
    parameters=[
        OpenApiParameter(
            name="name",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
    responses={
        (200, "application/json"): inline_serializer(
            "CreateJobResponse",
            fields={
                "job_id": serializers.IntegerField(),
            },
        ),
    }
)
@api_view(["GET"])
def create_job(request, version):
    serializer = CreateJobSerializer(data=request.GET)
    if not serializer.is_valid():
        raise ValidationError(serializer.errors)
    name = request.GET.get("name")
    job = Jobs.objects.create(
        type=JobTypes.test,
        status=JobStatus.on_progress,
        result=name,
    )
    task_id = async_task(
        "api.v1.v1_jobs.job.demo_q_func",
        name,
        hook="api.v1.v1_jobs.job.demo_q_response_func",
    )
    job.task_id = task_id
    job.save()
    return Response(
        {
            "job_id": job.id
        },
        status=status.HTTP_200_OK
    )
