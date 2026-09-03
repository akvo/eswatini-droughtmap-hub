"""Manage the reviewers assigned to an existing publication.

Reviewers used to be settable only in ``PublicationViewSet.perform_create``,
so a publication assigned the wrong reviewers — or a single-TWG roster, which
made every Inkhundla trivially "ready" and 100% agreed — was stuck that way for
its entire life. These two endpoints make that recoverable.

The two directions are deliberately asymmetric (D-11): adding can only ever
add information, while removing destroys a ``Review``. See ``ADDABLE_STATUSES``
and ``REMOVABLE_STATUSES``.

Mounted at /admin/publication-reviewers/, NOT under /admin/publication/{pk} —
that prefix has no trailing `$` and would swallow these routes (D-12).

Add and remove are two view classes rather than one class on two routes.
A single class put both handlers on both URLs: the schema then advertised
POST /{pk}/{user_id} and DELETE /{pk}, neither of which can run — the
handler signatures differ, so DRF passes the wrong kwargs and the request
dies with a TypeError (500, not 405). It also collided the operationIds,
which is why Swagger showed `publication_reviewers_add_2`. One class per
route keeps the documented surface and the callable surface identical.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_jobs.job import dispatch_review_request
from api.v1.v1_publication.models import Publication, Review
from api.v1.v1_publication.twg.serializers import (
    REMOVABLE_STATUSES,
    AssignReviewersSerializer,
)
from api.v1.v1_publication.serializers import PublicationSerializer
from utils.custom_permissions import IsAdmin
from utils.default_serializers import DefaultResponseSerializer


class ReviewerAssignmentAPI(APIView):
    """POST /admin/publication-reviewers/{pk} — add reviewers."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        operation_id="publication_reviewers_add",
        summary="Add reviewers to an existing publication",
        tags=["Publication"],
        request=AssignReviewersSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: DefaultResponseSerializer,
            404: DefaultResponseSerializer,
        },
    )
    def post(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        serializer = AssignReviewersSerializer(
            data=request.data, context={"publication": publication}
        )
        serializer.is_valid(raise_exception=True)

        subject = serializer.validated_data.get("subject")
        message = serializer.validated_data.get("message")
        added = 0
        for user in serializer.validated_data["reviewers"]:
            # get_or_create rather than create: re-posting an id that is
            # already assigned is a no-op, not a duplicate Review that
            # would double-count the reviewer's TWG coverage.
            review, created = Review.objects.get_or_create(
                publication=publication, user=user
            )
            if not created:
                continue
            added += 1
            if subject and message:
                dispatch_review_request(publication, review, subject, message)

        return Response(
            {
                "added": added,
                **PublicationSerializer(publication).data,
            },
            status=status.HTTP_200_OK,
        )


class ReviewerRemovalAPI(APIView):
    """DELETE /admin/publication-reviewers/{pk}/{user_id} — remove one."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        operation_id="publication_reviewers_remove",
        summary="Remove a reviewer who has not submitted",
        tags=["Publication"],
        responses={
            204: None,
            400: DefaultResponseSerializer,
            404: DefaultResponseSerializer,
        },
    )
    def delete(self, request, version, pk, user_id):
        publication = get_object_or_404(Publication, pk=pk)
        review = get_object_or_404(
            Review, publication=publication, user_id=user_id
        )

        if publication.status not in REMOVABLE_STATUSES:
            return Response(
                {
                    "reviewers": [
                        "Reviewers can only be removed while the publication "
                        "is still in review."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # A submitted review is an input other people's decisions were made
        # against — including the `majority_category` already snapshotted onto
        # submitted ValidationDecision rows. Deleting it would retroactively
        # change numbers the admin has already acted on (D-11).
        if review.is_completed:
            return Response(
                {
                    "reviewers": [
                        f"{review.user.name} has already submitted a review "
                        "and cannot be removed."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
