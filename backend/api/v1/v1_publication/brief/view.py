from django.shortcuts import get_object_or_404
from django_q.tasks import async_task
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_publication.models import Administration, BriefForwardLog
from .serializers import (
    BriefForwardRequestSerializer,
    BriefSituationResponseSerializer,
)
from .situation import build_situation


class BriefForwardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Forward a generated brief to a list of recipients",
        description=(
            "Requires TWG membership. Accepts a list of recipients, the "
            "Inkhundla ID and name, the components included in the brief, "
            "the URL of the brief, and an optional note. Queues an email "
            "task to send the brief to the recipients. Returns 202 with the "
            "number of recipients queued."
        ),
        responses={202: {"queued": True, "recipient_count": 0}},
        tags=["Brief Builder"],
    )
    def post(self, request, *args, **kwargs):
        if request.user.technical_working_group is None:
            return Response(
                {"detail": "TWG membership required to forward briefs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = BriefForwardRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        log = BriefForwardLog.objects.create(
            sender=request.user,
            recipients_payload=d["recipients"],
            inkhundla_id=d["inkhundla_id"],
            inkhundla_name=d["inkhundla_name"],
            components=d["components"],
            brief_url=d["brief_url"],
            note=d.get("note", ""),
        )
        async_task(
            "api.v1.v1_publication.brief.tasks.send_brief_forward_emails",
            log.pk,
        )
        return Response(
            {"queued": True, "recipient_count": len(d["recipients"])},
            status=status.HTTP_202_ACCEPTED,
        )


class BriefSituationView(APIView):
    """Generated "Situation this period" draft for one Inkhundla.

    IsAuthenticated, matching the page it serves — every source it composes
    from (/risk-levels, /iks) is already public, so a stricter gate here would
    be theatre.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generated situation draft for one Inkhundla",
        description=(
            "Narrative draft assembled from the validated D-class, the "
            "drought trend and this cycle's IKS submissions. A clause whose "
            "source is silent is omitted; `meta.sources` lists the ones that "
            "fired. Returns 200 with an empty `value` when every source is "
            "silent."
        ),
        responses={200: BriefSituationResponseSerializer},
        tags=["Brief Builder"],
    )
    def get(self, request, administration_id, version=None, *args, **kwargs):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        return Response(
            build_situation(administration), status=status.HTTP_200_OK
        )
