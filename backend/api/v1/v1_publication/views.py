import requests
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
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
from django.http import HttpResponse
from django.conf import settings
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
)
from api.v1.v1_publication.models import (
    Administration,
    Review,
    Publication,
)
from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    PublicationStatus,
)
from utils.custom_permissions import IsReviewer, IsAdmin
from utils.custom_pagination import Pagination
from utils.default_serializers import DefaultResponseSerializer
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
        return Review.objects.filter(
            user_id=user.id
        ).order_by("-publication__due_date")

    def list(self, request, *args, **kwargs):
        """
        Override the list method to add extra context.
        """
        queryset = self.get_queryset()
        total = Administration.objects.count()

        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={
                    "request": request, "total": total
                }
            )
            return self.get_paginated_response(serializer.data)

        # For non-paginated response (fallback)
        serializer = self.get_serializer(
            queryset,
            many=True,
            context={
                "request": request, "total": total
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        """
        Use different serializers for list and detail views.
        """
        if self.action == 'list':
            return ReviewListSerializer
        return ReviewSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        kwargs["context"]["total"] = Administration.objects.count()
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        if not self.request.data.get("publication_id"):
            raise ValidationError({
                "publication_id": "This field is required."
            })
        serializer.save(
            user_id=self.request.user.id,
            publication_id=self.request.data["publication_id"],
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response(
                {
                    "message": (
                        "You do not have permission to delete this review."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


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
                type=OpenApiTypes.NUMBER,
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
                f"{settings.GEONODE_BASE_URL}/api/v2/resources/{cdi_id}"
            )
            data = response.json().get("resource", None)
            if response.status_code == 200 and data:
                publication = Publication.objects.filter(
                    cdi_geonode_id=cdi_id
                ).first()
                return Response(
                    CDIGeonodeListSerializer(
                        instance={
                            **data,
                            "year_month": data.get("date"),
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
        page = int(request.GET.get("page", "1"))
        url = (
            "{0}/api/v2/resources?filter{{category.identifier}}={1}&page={2}"
            .format(
                settings.GEONODE_BASE_URL,
                category,
                page,
            )
        )
        username = settings.GEONODE_ADMIN_USERNAME
        password = settings.GEONODE_ADMIN_PASSWORD
        response = requests.get(
            url,
            auth=(username, password),
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
                publications_query = publications_query.filter(
                    status=publication_status
                )

            # Optimize lookup by creating a dictionary of publications
            publications_dict = {
                publication.cdi_geonode_id: {
                    "id": publication.pk,
                    "status": publication.status
                }
                for publication in publications_query
            }
            # Merge publication data into serialized_data
            for item in serialized_data:
                publication = publications_dict.get(
                    int(item["pk"])
                )
                if publication:
                    item["publication_id"] = publication["id"]
                    item["status"] = publication["status"]
            if publication_status:
                serialized_data = list(filter(
                    lambda s: s["publication_id"],
                    serialized_data
                ))
                data["total"] = len(serialized_data)
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
        return Publication.objects.all().order_by("-due_date")

    def get_serializer_class(self):
        if self.action == "list":
            return PublicationInfoSerializer
        if self.action == 'create':
            return CreatePublicationSerializer
        return PublicationSerializer

    def perform_create(self, serializer):
        # Exclude reviewers from the data
        reviewers = serializer.validated_data.pop("reviewers", [])
        publication = serializer.save()
        for reviewer in reviewers:
            Review.objects.create(
                publication=publication,
                user=reviewer
            )
        return PublicationSerializer(
            instance=publication
        ).data


class PublicationReviewsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch publication reviews",
        description="Fetch reviews for a specific publication",
        tags=["Admin"],
        responses={
            200: PublicationReviewsSerializer,
            400: DefaultResponseSerializer,
            500: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        reviews = Review.objects.filter(
            publication=publication,
            completed_at__isnull=False,
            is_completed=True
        )
        return Response(
            {
                "id": pk,
                "reviews": ReviewListSerializer(
                    instance=reviews,
                    many=True
                ).data
            },
            status=status.HTTP_200_OK
        )
