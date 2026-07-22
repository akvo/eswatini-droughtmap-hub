"""Track 2: admin validation queue — "This month drought validation" APIs.

Endpoints (publication-scoped, IsAuthenticated + IsAdmin):
- stats            -> the 4 summary cards + the publish gate
- administrations  -> queue table, searched / status-filtered / paginated

Mounted under /admin/validation/{pk}/ rather than /admin/publication/{pk}/:
that prefix is registered without a trailing `$`, so Django's resolver would
match it first and serve PublicationViewSet.retrieve with a 200 and the wrong
body instead of a 404 (D-3).

Per-Inkhundla validation is NOT written here — it has its own single-entry
write path on the decision page. This queue is read-only.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404

from api.v1.v1_publication.constants import AgreementFilter, ValidationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.validation.decision import (
    build_decision_payload,
    build_history,
    build_meta,
    build_reviews,
    bulk_validate,
    has_submitted,
    majority_of,
    mask_reviews,
    neighbours,
    save_decision,
)
from api.v1.v1_publication.validation.serializers import (
    ValidationBulkSerializer,
    ValidationDecisionFilterSerializer,
    ValidationDecisionWriteSerializer,
    ValidationMetaSerializer,
    ValidationQueueFilterSerializer,
)
from api.v1.v1_publication.constants import is_validated
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import ValidationDecision
from api.v1.v1_publication.validation.utils import (
    build_validation_stats,
    ordered_rows,
)
from utils.custom_pagination import Pagination
from utils.custom_permissions import IsAdmin
from utils.default_serializers import DefaultResponseSerializer

_FILTER_PARAMS = [
    OpenApiParameter(
        name="search",
        required=False,
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
    ),
    OpenApiParameter(
        name="status",
        required=False,
        enum=list(ValidationStatus.FieldStr.keys()),
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
    ),
    OpenApiParameter(
        name="agreement",
        required=False,
        enum=list(AgreementFilter.FieldStr.keys()),
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
    ),
]


def _rows(publication, request):
    serializer = ValidationQueueFilterSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return ordered_rows(publication, **serializer.filters())


class ValidationStatsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Validation-queue summary cards + publish gate",
        tags=["Validation"],
        responses={
            200: inline_serializer(
                "ValidationStatsResponse",
                fields={
                    "meta": serializers.JSONField(),
                    "data": serializers.JSONField(),
                },
            ),
            404: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        # Cards count the WHOLE publication, never the filtered view: the
        # numbers describe validation progress, not the current search.
        rows = ordered_rows(publication)
        return Response(
            {
                "meta": ValidationMetaSerializer(publication).data,
                "data": build_validation_stats(rows),
            },
            status=status.HTTP_200_OK,
        )


class ValidationAdministrationsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        operation_id="validation_administrations_list",
        summary="Validation queue (per-Inkhundla, filtered + paginated)",
        tags=["Validation"],
        parameters=_FILTER_PARAMS + [
            OpenApiParameter(
                name="page",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="page_size",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 404: DefaultResponseSerializer},
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        rows = _rows(publication, request)
        paginator = Pagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(page)


class ValidationBulkAPI(APIView):
    """Validate every ready + undisputed Inkhundla in one go.

    Deliberately takes no list of ids and no status: the server re-derives the
    set so the write can never exceed what the filter showed (D-3, TC-3).
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        operation_id="validation_bulk_validate",
        summary="Bulk-validate the non-disputed, fully reviewed Tinkhundla",
        tags=["Validation"],
        request=ValidationBulkSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: DefaultResponseSerializer,
            404: DefaultResponseSerializer,
        },
    )
    def post(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        serializer = ValidationBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = bulk_validate(
            publication,
            request.user,
            search=serializer.validated_data.get("search") or None,
        )
        message = f"{result['validated']} Tinkhundla validated."
        if result["skipped_drafts"]:
            message += (
                f" {result['skipped_drafts']} skipped — "
                "they have unsaved drafts."
            )
        return Response(
            {**result, "message": message}, status=status.HTTP_200_OK
        )


def _row_or_404(publication, administration_id):
    row = next(
        (
            r for r in ordered_rows(publication)
            if r["administration_id"] == administration_id
        ),
        None,
    )
    if row is None:
        raise Http404("Administration not part of this publication.")
    return row


class ValidationDecisionAPI(APIView):
    """One Inkhundla: the decision context (GET) and the decision (PUT).

    GET is IsAuthenticated — a non-NDRMA TWG member may view the page but
    sees colleagues' D-classes only after submitting their own. PUT is
    IsAdmin, so the reviewer's Submit is rejected by the permission class
    rather than by a hidden button.
    """

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @extend_schema(
        operation_id="validation_decision_retrieve",
        summary="Validation decision context for one Inkhundla",
        tags=["Validation"],
        parameters=_FILTER_PARAMS + [
            OpenApiParameter(
                name="page_size",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 404: DefaultResponseSerializer},
    )
    def get(self, request, version, pk, administration_id):
        publication = get_object_or_404(Publication, pk=pk)
        administration_id = int(administration_id)
        row = _row_or_404(publication, administration_id)

        serializer = ValidationDecisionFilterSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)

        reviews = build_reviews(publication, administration_id)
        masked = (
            request.user.role == UserRoleTypes.reviewer
            and not has_submitted(reviews, request.user.id)
        )
        payload = build_decision_payload(
            publication,
            row,
            mask_reviews(reviews, request.user.id) if masked else reviews,
            masked,
        )
        payload["meta"] = build_meta(
            publication,
            request.user,
            neighbours(
                publication, administration_id, **serializer.filters()
            ),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="validation_decision_update",
        summary="Save the validation decision as a draft, or submit it",
        tags=["Validation"],
        request=ValidationDecisionWriteSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: DefaultResponseSerializer,
            404: DefaultResponseSerializer,
        },
    )
    def put(self, request, version, pk, administration_id):
        publication = get_object_or_404(Publication, pk=pk)
        administration_id = int(administration_id)
        _row_or_404(publication, administration_id)
        administration = get_object_or_404(
            Administration, pk=administration_id
        )

        reviews = build_reviews(publication, administration_id)
        categories = [
            r["category"] for r in reviews if is_validated(r.get("category"))
        ]
        instance = ValidationDecision.objects.filter(
            publication=publication, administration=administration
        ).first()

        serializer = ValidationDecisionWriteSerializer(
            data=request.data,
            context={"categories": categories, "instance": instance},
        )
        serializer.is_valid(raise_exception=True)

        majority, is_tie = majority_of(categories)
        decision = save_decision(
            publication,
            administration,
            request.user,
            serializer.validated_data,
            majority,
            is_tie,
        )
        return Response(
            {
                "category": decision.category,
                "reasoning": decision.reasoning,
                "is_draft": decision.is_draft,
                "is_override": decision.is_override,
                "majority_category": decision.majority_category,
                "validated_at": decision.validated_at,
                "updated_at": decision.updated_at,
            },
            status=status.HTTP_200_OK,
        )


class ValidationHistoryAPI(APIView):
    """Prior validated decisions for this Inkhundla (AC-7.1)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="validation_decision_history",
        summary="Validation history for one Inkhundla, earlier cycles only",
        tags=["Validation"],
        parameters=[
            OpenApiParameter(
                name="limit",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 404: DefaultResponseSerializer},
    )
    def get(self, request, version, pk, administration_id):
        publication = get_object_or_404(Publication, pk=pk)
        administration_id = int(administration_id)
        try:
            limit = int(request.query_params.get("limit", 6))
        except (TypeError, ValueError):
            limit = 6
        return Response(
            {
                "administration_id": administration_id,
                "data": build_history(
                    publication, administration_id, limit=max(limit, 1)
                ),
            },
            status=status.HTTP_200_OK,
        )
