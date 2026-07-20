import time
import requests
from datetime import datetime
import geopandas as gpd
import topojson as tp
import matplotlib.pyplot as plt
import os
import json
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from matplotlib.patches import Patch
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiParameter
)
from django.core.management import call_command
from django.http import HttpResponse, Http404
from django.conf import settings
from django_q.tasks import async_task
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models.functions import TruncMonth
from jsmin import jsmin
from api.v1.v1_publication.serializers import (
    ReviewListSerializer,
    ReviewSerializer,
    CDIGeonodeListSerializer,
    CDIGeonodeFilterSerializer,
    PublicationSerializer,
    PublicationInfoSerializer,
    CreatePublicationSerializer,
    PublicationReviewsSerializer,
    ReviewInfoSerializer,
    ExportMapSerializer,
    PublishedMapSerializer,
    CompareMapSerializer,
    AttachRasterSerializer,
    PublicationRasterItemSerializer,
)
from api.v1.v1_publication.models import (
    Review,
    Publication,
    PublicationRaster,
)
from api.v1.v1_publication.constants import (
    GEONODE_SSL_VERIFY,
    GEONODE_REQUEST_TIMEOUT,
    CDIGeonodeCategory,
    PublicationStatus,
    DroughtCategory,
    ExportMapTypes,
    DroughtCategoryColor,
    FilterStatus,
)
from api.v1.v1_jobs.models import Jobs, JobTypes, JobStatus
from api.v1.v1_publication.utils import discover_components, geonode_auth
from utils.custom_permissions import IsReviewer, IsAdmin
from utils.custom_pagination import Pagination
from utils.default_serializers import (
    DefaultResponseSerializer,
    CommonOptionSerializer,
)
from utils.custom_serializer_fields import validate_serializers_message
from math import ceil


@extend_schema(
    description="Get required configuration",
    tags=["Development"],
    responses={200: {"type": "string", "format": "binary"}},
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


@extend_schema(
    responses={200: ReviewSerializer},
    tags=["Reviewer"],
    description="Manage publication reviews",
)
class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsReviewer]
    pagination_class = Pagination

    def get_queryset(self):
        user = self.request.user
        queryset = Review.objects.filter(
            user_id=user.id
        ).order_by("-created_at")
        params = self.request.query_params
        # All / Pending / Completed tabs (missing or "all" -> no filter)
        status_filter = params.get("status")
        if status_filter == FilterStatus.pending:
            queryset = queryset.filter(is_completed=False)
        elif status_filter == FilterStatus.completed:
            queryset = queryset.filter(is_completed=True)
        # Date-range filter on the review period (publication.year_month).
        # year_month is stored with an arbitrary day, so compare by month:
        # truncate the stored value and snap both bounds to day 1.
        # Invalid/absent dates parse to None -> that bound is skipped.
        start_date = parse_date(params.get("start_date") or "")
        end_date = parse_date(params.get("end_date") or "")
        if start_date or end_date:
            queryset = queryset.annotate(
                ym=TruncMonth("publication__year_month")
            )
        if start_date:
            queryset = queryset.filter(ym__gte=start_date.replace(day=1))
        if end_date:
            queryset = queryset.filter(ym__lte=end_date.replace(day=1))
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                required=False,
                enum=list(FilterStatus.FieldStr.keys()),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter reviews by completion state.",
            ),
            OpenApiParameter(
                name="start_date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Include reviews whose month >= this date.",
            ),
            OpenApiParameter(
                name="end_date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Include reviews whose month <= this date.",
            ),
        ],
        responses={200: ReviewListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """
        Override the list method to add extra context.
        """
        queryset = self.get_queryset()

        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page,
            many=True,
        )
        return self.get_paginated_response(serializer.data)

    def get_serializer_class(self):
        """
        Use different serializers for list and detail views.
        """
        if self.action == 'list':
            return ReviewListSerializer
        return ReviewSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return super().get_serializer(*args, **kwargs)

    def perform_update(self, serializer):
        review_id = self.kwargs.get('pk')
        is_completed = Review.objects.get(id=review_id).is_completed

        instance = serializer.save()
        publication = instance.publication
        if not is_completed and instance.is_completed:
            job = Jobs.objects.create(
                type=JobTypes.review_completed,
                status=JobStatus.on_progress,
                result=ReviewSerializer(instance).data,
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_review_completed",
                instance.user.name,
                publication.year_month.strftime("%Y-%m"),
                publication.id,
                instance.id,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            job.task_id = task_id
            job.save()
        # If all reviews are completed, update the publication status
        if (
            publication.reviews.filter(is_completed=False).count() == 0 and
            publication.status == PublicationStatus.in_review
        ):
            publication.status = PublicationStatus.in_validation
            publication.save()

    def perform_create(self, serializer):
        if not self.request.data.get("publication_id"):
            raise ValidationError({
                "publication_id": "This field is required."
            })
        serializer.save(
            user_id=self.request.user.id,
            publication_id=self.request.data["publication_id"],
        )


class CDIGeonodeAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch CDI Geonode resources",
        description=(
            "Fetch geodata resources from a specific category "
            "to start publication process"
        ),
        tags=["Admin"],
        parameters=[
            OpenApiParameter(
                name="page",
                default=1,
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="category",
                default=CDIGeonodeCategory.cdi,
                required=False,
                enum=CDIGeonodeCategory.FieldStr.keys(),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="status",
                required=False,
                enum=PublicationStatus.FieldStr.keys(),
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="id",
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="sort",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="sort_order",
                required=False,
                enum=["asc", "desc"],
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        request=CDIGeonodeFilterSerializer,
        responses={
            200: CDIGeonodeListSerializer(many=True),
            (200, "application/json"): inline_serializer(
                "CDIGeonodeListResponse",
                fields={
                    "current": serializers.IntegerField(),
                    "total": serializers.IntegerField(),
                    "total_page": serializers.IntegerField(),
                    "data": CDIGeonodeListSerializer(many=True),
                },
            ),
            400: DefaultResponseSerializer,
            500: DefaultResponseSerializer,
        },
    )
    def get(self, request, *args, **kwargs):
        serializer = CDIGeonodeFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            raise ValidationError({
                "message": "Invalid category parameter."
            })
        if serializer.validated_data.get(
            "id"
        ):
            cdi_id = serializer.validated_data["id"]
            response = requests.get(
                f"{settings.GEONODE_BASE_URL}/api/v2/resources/{cdi_id}",
                auth=geonode_auth(),
                verify=GEONODE_SSL_VERIFY,
                timeout=GEONODE_REQUEST_TIMEOUT,
            )
            data = response.json().get("resource", None)
            if response.status_code == 200 and data:
                publication = Publication.objects.filter(
                    cdi_geonode_id=cdi_id
                ).first()
                year_month = publication.year_month \
                    if publication else data.get("date")
                return Response(
                    CDIGeonodeListSerializer(
                        instance={
                            **data,
                            "year_month": year_month,
                            "publication_id": (
                                publication.pk if publication else None
                            ),
                            "status": (
                                publication.status if publication else None
                            ),
                        }
                    ).data,
                    status=status.HTTP_200_OK
                )
            return Response(
                {"message": "Server Error: Unable to fetch data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        category = serializer.validated_data.get(
            "category",
            CDIGeonodeCategory.cdi
        )
        publication_status = serializer.validated_data.get(
            "status",
            None
        )
        sort_field = serializer.validated_data.get("sort", None)
        sort_order = serializer.validated_data.get("sort_order", "desc")
        page = int(request.GET.get("page", "1"))
        url = (
            "{0}/api/v2/resources"
            "?filter{{category.identifier}}={1}"
            "&filter{{subtype}}=raster&page={2}&sort[]=-date"
            .format(
                settings.GEONODE_BASE_URL,
                category,
                page,
            )
        )
        if publication_status:
            ids = Publication.objects.filter(
                status=publication_status
            ).values_list("cdi_geonode_id", flat=True)
            if len(ids):
                filter_ids = "&".join(
                    [
                        f"filter{{pk.in}}={id}"
                        for id in ids
                    ]
                )
                url = (
                    "{0}/api/v2/resources?{1}".format(
                        settings.GEONODE_BASE_URL,
                        filter_ids
                    )
                )
                url = f"{url}&page={page}&sort[]=-date"
        response = requests.get(
            url,
            auth=geonode_auth(),
            verify=GEONODE_SSL_VERIFY,
            timeout=GEONODE_REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            # Prepare the serialized data
            serialized_data = [
                CDIGeonodeListSerializer(
                    instance={
                        **item,
                        "year_month": item.get("date"),
                        "publication_id": None,
                        "status": None,
                    }
                ).data
                for item in data.get("resources", [])
            ]

            # Extract IDs from serialized data
            cdi_geonode_ids = [int(item["pk"]) for item in serialized_data]

            # Fetch related publications based on the IDs and status
            publications_query = Publication.objects.filter(
                cdi_geonode_id__in=cdi_geonode_ids
            )
            if publication_status:
                publications_query = Publication.objects.filter(
                    status=publication_status
                )

            # Optimize lookup by creating a dictionary of publications
            publications_dict = {
                publication.cdi_geonode_id: {
                    "id": publication.pk,
                    "status": publication.status,
                    "year_month": publication.year_month
                }
                for publication in publications_query.all()
            }
            # Merge publication data into serialized_data
            for item in serialized_data:
                publication = publications_dict.get(
                    int(item["pk"])
                )
                if publication:
                    item["year_month"] = publication["year_month"]
                    item["publication_id"] = publication["id"]
                    item["status"] = publication["status"]

            # Apply server-side sorting
            if sort_field:
                reverse = sort_order == "desc"
                # Normalize sort key to handle mixed types (str vs date/datetime)
                def normalize_sort_key(value, field_name):
                    if value is None:
                        return ""
                    # For year_month and created fields, convert dates to ISO strings
                    if field_name in ("year_month", "created"):
                        if hasattr(value, "isoformat"):
                            return value.isoformat()
                        return str(value)
                    return value

                serialized_data.sort(
                    key=lambda x: (
                        x.get(sort_field) is not None,
                        normalize_sort_key(x.get(sort_field), sort_field)
                    ),
                    reverse=reverse
                )

            if publication_status:
                data["total"] = publications_query.count()
            total_page = ceil(int(data["total"]) / int(data["page_size"]))
            return Response(
                {
                    "current": page,
                    "total": data["total"],
                    "total_page": total_page,
                    "data": serialized_data
                },
                status=status.HTTP_200_OK
            )
        elif response.status_code == 400:
            return Response(
                {"message": "Bad Request: Invalid parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Server Error: Unable to fetch data."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    responses={200: PublicationSerializer},
    tags=["Admin"],
    description="Manage publication process",
)
class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = Pagination

    def get_queryset(self):
        queryset = Publication.objects.all().order_by("-due_date")
        params = self.request.query_params
        status_filter = params.get("status")
        if status_filter == FilterStatus.pending:
            queryset = queryset.filter(
                status=PublicationStatus.in_validation
            )
        elif status_filter == FilterStatus.completed:
            queryset = queryset.filter(
                status=PublicationStatus.published
            )
        elif status_filter and status_filter != FilterStatus.all:
            try:
                queryset = queryset.filter(status=int(status_filter))
            except (ValueError, TypeError):
                pass
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PublicationInfoSerializer
        if self.action == 'create':
            return CreatePublicationSerializer
        return PublicationSerializer

    def perform_create(self, serializer):
        # Start a database transaction
        try:
            with transaction.atomic():
                # Exclude some fields from the data
                reviewers = serializer.validated_data.pop("reviewers", [])
                subject = serializer.validated_data.pop("subject")
                message = serializer.validated_data.pop("message")
                download_url = serializer.validated_data.pop("download_url")

                # Save the publication
                publication = serializer.save()

                publication.reviews.set([
                    Review(publication=publication, user=reviewer)
                    for reviewer in reviewers
                ], bulk=False)

                timestamp = int(time.time())
                filename = "raster_{0}_{1}.tif".format(
                    publication.cdi_geonode_id,
                    timestamp
                )
                # Create a job
                job = Jobs.objects.create(
                    type=JobTypes.download_geonode_dataset,
                    status=JobStatus.on_progress,
                    info={
                        "publication_id": publication.id,
                        "filename": filename,
                        "subject": subject,
                        "message": message,
                    },
                )
                hook = "download_geonode_dataset_results"
                task_id = async_task(
                    "api.v1.v1_jobs.job.download_geonode_dataset",
                    download_url,
                    filename,
                    hook=f"api.v1.v1_jobs.job.{hook}",
                )
                # Update the job with the task ID
                job.task_id = task_id
                job.save()

                # Queue component-raster discovery (ESI/EVI2/SM/SPI) as its
                # own job rather than running it inline: it walks the GeoNode
                # catalogue up to four times, and none of that should delay
                # or fail the publication the admin just asked for (D-6).
                # Independent of the CDI chain above, so reviewer emails are
                # never held up waiting on components.
                raster_job = Jobs.objects.create(
                    type=JobTypes.attach_component_rasters,
                    status=JobStatus.on_progress,
                    info={"publication_id": publication.id},
                )
                raster_job.task_id = async_task(
                    "api.v1.v1_jobs.job.attach_publication_rasters",
                    publication.id,
                    hook="api.v1.v1_jobs.job.job_done_hook",
                )
                raster_job.save()

                # Return the serialized publication data
                return PublicationSerializer(publication).data
        except IntegrityError as e:
            # Raise an appropriate exception if needed
            raise serializers.ValidationError({"messsage": f"{e}"})

    def perform_destroy(self, instance):
        instance.delete(hard=True)

    def perform_update(self, serializer):
        instance = serializer.save()
        total_adms = len(instance.initial_values)
        total_validated = 0
        if instance.validated_values:
            total_validated = len(list(filter(
                lambda x: x.get("category") or x.get("category") == 0,
                instance.validated_values
            )))
        instance.updated_at = timezone.now()
        if instance.narrative and total_adms == total_validated:
            instance.published_at = timezone.now()
        instance.save()


class ComponentRasterPreviewAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Preview component rasters available for a month",
        description=(
            "Which of ESI/EVI2/SM/SPI GeoNode currently holds for the given "
            "month. Advisory only: the attach job re-reads the catalogue "
            "after the publication is created and remains the source of "
            "truth."
        ),
        tags=["Admin"],
        parameters=[
            OpenApiParameter(
                name="year_month",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Target month as YYYY-MM.",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 400: DefaultResponseSerializer},
    )
    def get(self, request, version):
        year_month = request.GET.get("year_month", "")
        try:
            target_month = datetime.strptime(
                year_month[:7], "%Y-%m"
            ).strftime("%Y-%m")
        except ValueError:
            raise ValidationError({
                "year_month": "Invalid format. Use YYYY-MM."
            })
        return Response(
            {
                "data": discover_components(target_month),
                "meta": {"year_month": target_month},
            },
            status=status.HTTP_200_OK,
        )


class PublicationRasterAPI(APIView):
    # Class-level permission is JWT-only: GET (list) is available to any
    # authenticated user (admin or reviewer), while POST/DELETE additionally
    # gate on IsAdmin explicitly at the top of the method body, matching the
    # house style used by the mutating endpoints above.
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Attach an indicator raster to a publication",
        description=(
            "Resolve the GeoNode download URL for geonode_id server-side, "
            "create the PublicationRaster row, and queue the "
            "download-then-extract job chain."
        ),
        tags=["Admin"],
        request=AttachRasterSerializer,
        responses={
            201: AttachRasterSerializer,
            400: DefaultResponseSerializer,
            403: DefaultResponseSerializer,
        },
    )
    def post(self, request, version, pk, raster_id=None):
        # This method is only reachable from the list route
        # (.../rasters); the detail route (.../rasters/<raster_id>)
        # supplies raster_id and should 404 here instead of hitting the
        # "unexpected keyword argument" TypeError DRF would otherwise
        # surface as a 500.
        if raster_id is not None:
            raise Http404
        if not IsAdmin().has_permission(request, self):
            raise PermissionDenied()
        publication = get_object_or_404(Publication, pk=pk)

        serializer = AttachRasterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        geonode_id = serializer.validated_data["geonode_id"]

        # Resolve the download URL server-side rather than trusting the
        # client with it, so a caller can only ever attach GeoNode
        # resources the backend itself can see and authenticate against.
        response = requests.get(
            f"{settings.GEONODE_BASE_URL}/api/v2/resources/{geonode_id}",
            auth=geonode_auth(),
            verify=GEONODE_SSL_VERIFY,
            timeout=GEONODE_REQUEST_TIMEOUT,
        )
        resource = (
            response.json().get("resource")
            if response.status_code == 200 else None
        ) or {}
        download_url = resource.get("download_url")
        if response.status_code != 200 or not download_url:
            raise ValidationError({
                "geonode_id": "Unable to resolve GeoNode resource."
            })

        try:
            # Nested atomic() turns the uniqueness violation into a
            # savepoint rollback instead of poisoning the whole request's
            # transaction, so the 400 response can still be built normally.
            # The job creation + async_task dispatch live inside this same
            # block (matching PublicationViewSet.perform_create's pattern
            # above) so that a failure there rolls the raster row back too,
            # instead of leaving an orphaned PublicationRaster with no job
            # that would then block re-attaching via the unique constraint.
            with transaction.atomic():
                raster = serializer.save(publication=publication)

                timestamp = int(time.time())
                filename = "raster_{0}_{1}_{2}.tif".format(
                    publication.id, raster.indicator, timestamp
                )
                job = Jobs.objects.create(
                    type=JobTypes.download_geonode_dataset,
                    status=JobStatus.on_progress,
                    info={
                        "publication_raster_id": raster.id,
                        "filename": filename,
                    },
                )
                task_id = async_task(
                    "api.v1.v1_jobs.job.download_geonode_dataset",
                    download_url,
                    filename,
                    hook=(
                        "api.v1.v1_jobs.job."
                        "download_indicator_dataset_results"
                    ),
                )
                job.task_id = task_id
                job.save()
        except IntegrityError:
            raise ValidationError({
                "indicator": (
                    "This indicator is already attached to the publication."
                )
            })

        return Response(
            AttachRasterSerializer(raster).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="List indicator rasters attached to a publication",
        tags=["Admin"],
        responses={200: PublicationRasterItemSerializer(many=True)},
    )
    def get(self, request, version, pk, raster_id=None):
        # Same list-route-only guard as post() above.
        if raster_id is not None:
            raise Http404
        publication = get_object_or_404(Publication, pk=pk)
        return Response(
            {
                "data": PublicationRasterItemSerializer(
                    publication.rasters.all(), many=True
                ).data,
                "meta": {
                    "publication": publication.id,
                    "year_month": publication.year_month.strftime("%Y-%m"),
                },
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Detach an indicator raster from a publication",
        tags=["Admin"],
        responses={204: None, 403: DefaultResponseSerializer},
    )
    def delete(self, request, version, pk, raster_id=None):
        # Mirror image of the list-route guards above: this method only
        # lives on the detail route (.../rasters/<raster_id>), so a
        # DELETE against the list route (no raster_id) should 404
        # instead of hitting a "missing positional argument" TypeError.
        if raster_id is None:
            raise Http404
        if not IsAdmin().has_permission(request, self):
            raise PermissionDenied()
        raster = get_object_or_404(
            PublicationRaster, pk=raster_id, publication_id=pk
        )
        raster.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicationReviewsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch publication reviews",
        description="Fetch reviews for a specific publication",
        tags=["Admin"],
        parameters=[
            OpenApiParameter(
                name="non_disputed",
                required=False,
                default=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="non_validated",
                required=False,
                default=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: PublicationReviewsSerializer,
            400: DefaultResponseSerializer,
            500: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)

        non_disputed = request.GET.get("non_disputed") in ["true", "1"]
        non_validated = request.GET.get("non_validated") in ["true", "1"]

        return Response(
            PublicationReviewsSerializer(
                instance=publication,
                context={
                    "non_disputed": non_disputed,
                    "non_validated": non_validated
                }
            ).data,
            status=status.HTTP_200_OK
        )


class ReviewDetailsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch review details as an Admin",
        description="Fetch data for a specific review",
        tags=["Admin"],
        responses=ReviewInfoSerializer,
    )
    def get(self, request, version, pk):
        review = get_object_or_404(Review, pk=pk)

        return Response(
            ReviewInfoSerializer(
                instance=review,
            ).data,
            status=status.HTTP_200_OK
        )


class ExportMapAPI(APIView):

    @extend_schema(
        summary="Export Public Map",
        description=(
            "Export published map as GeoJSON, Shapefile, PNG, or SVG."
        ),
        tags=["Map"],
        parameters=[
            OpenApiParameter(
                name="export_type",
                default=ExportMapTypes.geojson,
                required=False,
                enum=ExportMapTypes.FieldStr.keys(),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiTypes.BINARY,  # Binary response for file downloads
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        if publication.status != PublicationStatus.published:
            raise ValidationError({
                "message": "Map not yet published"
            })

        # Validate the requested format
        serializer = ExportMapSerializer(data=request.query_params)
        if not serializer.is_valid():
            raise ValidationError({
                "message": "Invalid format parameter."
            })

        try:
            # Get the requested format from query parameters
            type = serializer.validated_data.get(
                "export_type",
                ExportMapTypes.geojson
            )

            # Load your GeoDataFrame
            gdf = self._load_geodataframe(publication.validated_values)

            # Handle the export based on the requested format
            year_month = publication.year_month.strftime('%Y-%m')
            if type == ExportMapTypes.geojson:
                return self._export_geojson(gdf, year_month)
            elif type == ExportMapTypes.shapefile:
                return self._export_shapefile(gdf, year_month)
            elif type == ExportMapTypes.png:
                return self._export_image(gdf, year_month, "png")
            elif type == ExportMapTypes.svg:
                return self._export_image(gdf, year_month, "svg")
        except Exception as e:
            return Response(
                {
                    "message": f"An error occurred during export: {e}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _load_geodataframe(self, validated_values):
        # Step 1: Load the TopoJSON file
        with open("./source/eswatini.topojson", "r") as f:
            topojson_data = json.load(f)
        validated_dict = {
            item["administration_id"]: item["category"]
            for item in validated_values
        }
        # Step 2: Convert TopoJSON to GeoJSON using the topojson library
        # Create a Topology object from the loaded TopoJSON data
        topology = tp.Topology(topojson_data, object_name="eswatini")
        # Convert the TopoJSON to GeoJSON
        geojson_data = topology.to_geojson()

        # Step 3: Load the GeoJSON data into a GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(json.loads(geojson_data))

        # Step 4: Map the categories to the GeoDataFrame
        gdf["category"] = gdf["administration_id"].map(validated_dict)

        # Step 5: Add the "cat_name" column
        gdf["cat_name"] = gdf["category"].map(
            DroughtCategory.FieldStr.get
        )

        # Step 6: Handle missing values (optional)
        gdf["category"] = gdf["category"].fillna(DroughtCategory.none)
        gdf["cat_name"] = gdf["cat_name"].fillna(
            DroughtCategory.FieldStr[DroughtCategory.none]
        )
        # Ensure the GeoDataFrame has a CRS
        if gdf.crs is None:
            # Assign a default CRS (e.g., WGS84, EPSG:4326)
            gdf.set_crs("EPSG:4326", inplace=True)
        return gdf

    def _export_geojson(self, gdf, year_month):
        """
        Export the GeoDataFrame as GeoJSON.
        """
        geojson_data = gdf.to_json()
        response = HttpResponse(geojson_data, content_type="application/json")
        cd = f'attachment; filename="cdi_map_{year_month}.geojson"'
        response["Content-Disposition"] = cd
        return response

    def _export_shapefile(self, gdf, year_month):
        """
        Export the GeoDataFrame as a Shapefile (zipped).
        """
        # Rename `administration_id` column to `adm_id` in gdf
        gdf = gdf.rename(columns={"administration_id": "adm_id"})

        # Create an in-memory buffer for the Shapefile
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            # Write the Shapefile components to the zip file
            temp_dir = "./tmp"
            os.makedirs(
                temp_dir,
                exist_ok=True
            )
            gdf.to_file(
                os.path.join(temp_dir, f"cdi_map_{year_month}.shp"),
                driver="ESRI Shapefile"
            )
            # Manually create the .prj file if it doesn't exist
            prj_path = os.path.join(
                temp_dir,
                f"cdi_map_{year_month}.prj"
            )
            if not os.path.exists(prj_path):
                with open(prj_path, "w") as prj_file:
                    prj_file.write(gdf.crs.to_wkt())

            for ext in ["shp", "shx", "dbf", "prj"]:
                file_path = os.path.join(
                    temp_dir,
                    f"cdi_map_{year_month}.{ext}"
                )
                zip_file.write(
                    file_path,
                    arcname=f"cdi_map_{year_month}.{ext}"
                )
                os.remove(file_path)  # Clean up temporary files

        # Prepare the HTTP response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type="application/zip")
        cd = f'attachment; filename="cdi_map_{year_month}.zip"'
        response["Content-Disposition"] = cd
        return response

    def _export_image(self, gdf, year_month, format):
        """
        Export the GeoDataFrame as an image (SVG or PNG).
        """
        if format not in ["svg", "png"]:
            raise ValidationError({
                "message": (
                    "Invalid format parameter."
                    "Only 'svg' and 'png' are supported."
                )
            })

        # Define a custom color mapping for categories
        color_mapping = dict(DroughtCategoryColor.FieldStr.items())

        # Ensure valid geometries
        gdf = gdf[gdf.is_valid & ~gdf.geometry.is_empty]

        fig, ax = plt.subplots(figsize=(10, 10))

        # Plot
        valid_categories = set(gdf["category"].unique())
        filtered_color_mapping = {
            k: v for k, v in color_mapping.items() if k in valid_categories
        }

        legend_patches = []  # Store patches for the legend
        for category, color in filtered_color_mapping.items():
            subset = gdf[gdf["category"] == category]
            subset.plot(
                ax=ax,
                color=color,
                edgecolor="black",
                label=DroughtCategory.FieldStr.get(category)
            )

            legend_patches.append(Patch(
                facecolor=color,
                edgecolor="black",
                label=DroughtCategory.FieldStr.get(category)
            ))

        # Fix aspect ratio and limits
        ax.set_xlim(gdf.total_bounds[0], gdf.total_bounds[2])
        ax.set_ylim(gdf.total_bounds[1], gdf.total_bounds[3])

        # Add legend to the plot
        if legend_patches:
            ax.legend(
                handles=legend_patches,
                loc="upper right",
                title="Drought Categories"
            )

        # Save as image
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format=format, bbox_inches="tight")
        plt.close(fig)

        img_buffer.seek(0)
        content_type = "image/svg+xml" if format == "svg" else "image/png"
        response = HttpResponse(img_buffer, content_type=content_type)
        cd = f'attachment; filename="cdi_map_{year_month}.{format}"'
        response["Content-Disposition"] = cd
        return response


class PublishedMapViewSet(viewsets.ModelViewSet):
    serializer_class = PublishedMapSerializer
    pagination_class = Pagination

    def get_queryset(self):
        return Publication.objects.filter(
            status=PublicationStatus.published,
            published_at__isnull=False
        ).order_by("-year_month")

    @extend_schema(
        responses={200: PublishedMapSerializer},
        tags=["Map"],
        description="Published maps list",
        parameters=[
            OpenApiParameter(
                name="left_date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="right_date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Override the list method to add extra context.
        """
        serializer = CompareMapSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"message": validate_serializers_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Paginate the queryset
        queryset = self.get_queryset()
        left_date = serializer.validated_data.get("left_date")
        right_date = serializer.validated_data.get("right_date")
        if left_date and right_date:
            queryset = queryset.filter(
                year_month__in=[left_date, right_date]
            )

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page,
            many=True,
        )
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        responses={200: PublishedMapSerializer},
        tags=["Map"],
        description="Published Map details",
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PublicationDateAPI(APIView):

    @extend_schema(
        description="Fetch all publication date of published maps",
        tags=["Map"],
        parameters=[
            OpenApiParameter(
                name="exclude_id",
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses=CommonOptionSerializer,
    )
    def get(self, request, version):
        queryset = Publication.objects.filter(
            status=PublicationStatus.published,
            published_at__isnull=False
        ).order_by("-year_month")
        exclude_id = request.GET.get("exclude_id")
        if exclude_id:
            queryset = queryset.exclude(pk=int(exclude_id))
        publications = queryset.all()
        options = [
            {
                "value": p.id,
                "label": p.year_month
            }
            for p in publications
        ]
        return Response(
            CommonOptionSerializer(
                instance=options,
                many=True,
            ).data,
            status=status.HTTP_200_OK
        )
