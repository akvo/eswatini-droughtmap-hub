from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.core.management import call_command
from django.http import HttpResponse
from jsmin import jsmin
from api.v1.v1_publication.serializers import (
    ReviewListSerializer,
    ReviewSerializer
)
from api.v1.v1_publication.models import (
    Administration,
    Review
)
from utils.custom_permissions import IsReviewer
from utils.custom_pagination import Pagination


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
        ).order_by("publication__due_date")

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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
