"""Tell the operator that fetched uploads are waiting (PA-6 OQ-14).

In the admin path the operator is present: they upload, and the report is
the response. A file fetched from GeoNode has nobody watching it, so a
`validated` row can sit unnoticed while the provider assumes publishing was
enough — which would make phase 2's experience worse than phase 1's, not
better.

The message is deliberately "a file is waiting for your review", not
"something was applied". Nothing is applied by the poller.
"""

import logging
from typing import List


from api.v1.v1_indicators.constants import UploadStatus
from api.v1.v1_users.models import SystemUser
from utils.email_helper import EmailTypes, send_email

logger = logging.getLogger(__name__)

__all__ = ["operator_recipients", "notify_pending_uploads"]

OPERATOR_GROUP = "Data operators"


def operator_recipients() -> List[str]:
    """Who reviews fetched uploads.

    The `Data operators` group first, because that is the role which can
    actually act on one. Superusers are the fallback so a misconfigured
    group does not mean the mail goes nowhere — silence is the failure mode
    this whole function exists to prevent.
    """
    emails = list(
        SystemUser.objects.filter(
            groups__name=OPERATOR_GROUP,
            deleted_at__isnull=True,
        ).values_list("email", flat=True)
    )
    if not emails:
        emails = list(
            SystemUser.objects.filter(
                is_superuser=True,
                deleted_at__isnull=True,
            ).values_list("email", flat=True)
        )
        if emails:
            logger.warning(
                "No members in '%s'; notifying superusers instead.",
                OPERATOR_GROUP,
            )
    return sorted(set(e for e in emails if e))


def notify_pending_uploads(uploads) -> List[str]:
    """Email operators about newly fetched uploads. Returns the recipients."""
    if not uploads:
        return []
    recipients = operator_recipients()
    if not recipients:
        logger.error(
            "Fetched %d upload(s) but found nobody to notify.", len(uploads)
        )
        return []

    pending = [u for u in uploads if u.status == UploadStatus.validated]
    rejected = [u for u in uploads if u.status == UploadStatus.rejected]
    lines = []
    for upload in pending:
        lines.append(
            f"{upload.dataset} — {upload.source_label} "
            f"({upload.as_of}), {upload.changed_count} value(s) would change"
        )
    for upload in rejected:
        lines.append(f"{upload.dataset} — REJECTED: {upload.source_label}")

    send_email(
        context={
            "send_to": recipients,
            "pending_count": len(pending),
            "rejected_count": len(rejected),
            "lines": lines,
        },
        type=EmailTypes.dataset_upload_pending,
    )
    return recipients
