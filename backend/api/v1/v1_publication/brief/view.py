from django_q.tasks import async_task
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_publication.models import BriefForwardLog
from .serializers import BriefForwardRequestSerializer


class BriefForwardView(APIView):
    permission_classes = [IsAuthenticated]

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
