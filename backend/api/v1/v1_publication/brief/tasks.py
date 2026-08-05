from utils.email_helper import send_email, EmailTypes
from api.v1.v1_publication.models import BriefForwardLog


def send_brief_forward_emails(log_pk: int):
    try:
        log = BriefForwardLog.objects.select_related("sender").get(pk=log_pk)
    except BriefForwardLog.DoesNotExist:
        return

    sender_name = (
        log.sender.name if log.sender and log.sender.name else "A TWG member"
    )

    for recipient in log.recipients_payload:
        email = recipient.get("email")
        if not email:
            continue
        recipient_name = recipient.get("name") or email
        send_email(
            context={
                "send_to": [email],
                "recipient_name": recipient_name,
                "sender_name": sender_name,
                "inkhundla_name": log.inkhundla_name,
                "note": log.note,
                "brief_url": log.brief_url,
            },
            type=EmailTypes.brief_forward,
        )
