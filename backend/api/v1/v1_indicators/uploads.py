"""Create, apply and revert DatasetUpload rows (PA-6).

Kept out of admin.py so the rules that matter — atomicity, idempotence,
"blank leaves the value alone" — are testable without a request.
"""

import logging
import os
from typing import List

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError

from api.v1.v1_indicators import parsers
from api.v1.v1_indicators.constants import UploadOrigin, UploadStatus
from api.v1.v1_indicators.datasets import DATASETS, lookup
from api.v1.v1_indicators.models import DatasetUpload, Indicator
from api.v1.v1_publication.models import Administration

logger = logging.getLogger(__name__)

__all__ = ["validate_extension", "create_uploads", "apply_upload",
           "revert_upload", "AppliedResult"]


def validate_extension(uploaded) -> None:
    name = getattr(uploaded, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext in {".xlsx", ".xls"}:
        # D-2: instructional, not a MIME complaint. A bare rejection here
        # sends the operator straight back to the tech team.
        raise ValidationError(
            "Excel workbooks are not accepted. In Excel choose "
            "File > Save As > CSV UTF-8, then upload the .csv file."
        )
    if ext not in parsers.ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '{ext or name}'. Upload a .csv file."
        )
    size = getattr(uploaded, "size", 0)
    if size and size > parsers.MAX_FILE_SIZE:
        raise ValidationError("File too large (max 2 MB for 59 rows).")


def create_uploads(uploaded, source_label, as_of, user,
                   origin=UploadOrigin.upload, geonode_id=None
                   ) -> List[DatasetUpload]:
    """One DatasetUpload per recognised value column (D-15).

    Writes nothing to Indicator — validation and apply are separate steps
    with a human between them (D-3).
    """
    validate_extension(uploaded)
    # Callers hand us whatever they have — the admin form a date, the CLI a
    # string. Coerce once here so `indicator_source` can format it and the
    # in-memory instance behaves like a reloaded one.
    if isinstance(as_of, str):
        parsed = parse_date(as_of)
        if parsed is None:
            raise ValidationError(
                f"as_of {as_of!r} is not a date (expected YYYY-MM-DD)."
            )
        as_of = parsed
    checksum = parsers.checksum_of(uploaded)
    administrations = list(Administration.objects.all())

    try:
        reports = parsers.parse(uploaded, administrations)
    except parsers.ParseError as error:
        reports = {}
        fatal = str(error)
    else:
        fatal = None

    if not reports:
        # Nothing recognised: store the attempt anyway, because the operator
        # needs to see why, and name the columns the platform accepts.
        detail = fatal or (
            "No dataset column found. Expected one or more of: "
            + ", ".join(sorted(d.field for d in DATASETS.values()))
        )
        return [
            _persist(
                uploaded, checksum, "unknown", source_label, as_of, user,
                origin, geonode_id, UploadStatus.rejected,
                {"errors": [{"code": "no_dataset_column", "detail": detail}],
                 "warnings": [], "diff": []},
            )
        ]

    # D-15: a column left empty for all 59 rows is skipped entirely — no
    # row, no report, nothing to dismiss. The template carries every dataset
    # column, so without this an operator filling one would generate ten
    # empty upload records to clear by hand.
    filled = {
        field: report
        for field, report in reports.items()
        if report["diff"] or report["errors"]
    }
    if not filled:
        return [
            _persist(
                uploaded, checksum, "unknown", source_label, as_of, user,
                origin, geonode_id, UploadStatus.rejected,
                {
                    "errors": [{
                        "code": "no_values",
                        "detail": (
                            "The file has recognised columns but every one "
                            "of them is empty, so there is nothing to "
                            "apply. Fill at least one column."
                        ),
                    }],
                    "warnings": [],
                    "diff": [],
                },
            )
        ]

    created = []
    for field, report in filled.items():
        definition = lookup(field)
        status = (
            UploadStatus.rejected
            if report["errors"]
            else UploadStatus.validated
        )
        created.append(
            _persist(
                uploaded, checksum, definition.slug, source_label, as_of,
                user, origin, geonode_id, status, report,
            )
        )
    return created


def _persist(uploaded, checksum, slug, source_label, as_of, user, origin,
             geonode_id, status, report) -> DatasetUpload:
    upload = DatasetUpload(
        dataset=slug,
        origin=origin,
        checksum=checksum,
        source_label=source_label,
        as_of=as_of,
        status=status,
        report=report,
        geonode_id=geonode_id,
        uploaded_by=user if getattr(user, "pk", None) else None,
    )
    uploaded.seek(0)
    # Siblings of one file each keep their own copy: cheap at this size, and
    # it keeps a row self-contained if another is deleted.
    upload.file.save(
        f"{slug}_{checksum[:12]}.csv",
        ContentFile(uploaded.read()),
        save=False,
    )
    upload.save()
    return upload


def _writable(field: str, value):
    """None is only storable where the column allows it.

    A revert (D-10) replays `before` values, and `before` is None for an
    Inkhundla that had no Indicator row at all. The eligibility columns are
    `default=0` and NOT NULL, so writing None there raises IntegrityError.
    Fall back to the column's own default rather than inventing a zero.
    """
    if value is not None:
        return value
    column = Indicator._meta.get_field(field)
    if column.null:
        return None
    return column.get_default()


class AppliedResult:
    def __init__(self, written=0, skipped=0):
        self.written = written
        self.skipped = skipped


@transaction.atomic
def apply_upload(upload: DatasetUpload, user) -> AppliedResult:
    """Write the diff to Indicator. Atomic, idempotent, changed rows only."""
    if upload.status != UploadStatus.validated:
        raise ValidationError(
            f"Only a validated upload can be applied; this one is "
            f"{upload.status_label.lower()}."
        )
    definition = upload.definition
    if definition is None:
        raise ValidationError(
            f"'{upload.dataset}' is no longer a known dataset."
        )

    written = 0
    skipped = 0
    for row in upload.report.get("diff", []):
        if row.get("before") == row.get("after"):
            skipped += 1
            continue
        Indicator.objects.update_or_create(
            administration_id=row["administration_id"],
            defaults={
                definition.field: _writable(definition.field, row["after"]),
                "source": upload.indicator_source,
                "as_of": upload.as_of,
                "is_placeholder": False,
            },
        )
        written += 1

    DatasetUpload.objects.filter(
        dataset=upload.dataset, status=UploadStatus.applied
    ).exclude(pk=upload.pk).update(status=UploadStatus.superseded)

    upload.status = UploadStatus.applied
    upload.applied_at = timezone.now()
    upload.applied_by = user if getattr(user, "pk", None) else None
    upload.save(update_fields=["status", "applied_at", "applied_by"])
    return AppliedResult(written=written, skipped=skipped)


@transaction.atomic
def revert_upload(upload: DatasetUpload, user) -> DatasetUpload:
    """Replay the stored `before` values as a new upload (D-10).

    Never mutates the applied row: the history stays append-only, so what
    the values are is always the last applied row.
    """
    if upload.status != UploadStatus.applied:
        raise ValidationError("Only an applied upload can be reverted.")

    inverted = [
        {
            "administration_id": row["administration_id"],
            "name": row["name"],
            "before": row["after"],
            "after": row["before"],
        }
        for row in upload.report.get("diff", [])
    ]
    reversal = DatasetUpload.objects.create(
        dataset=upload.dataset,
        origin=UploadOrigin.revert,
        file=upload.file,
        checksum=upload.checksum,
        source_label=f"Revert of upload #{upload.pk}: {upload.source_label}",
        as_of=upload.as_of,
        status=UploadStatus.validated,
        report={
            "dataset": upload.dataset,
            "field": upload.report.get("field"),
            "reverts": upload.pk,
            "errors": [],
            "warnings": [],
            "diff": inverted,
        },
        uploaded_by=user if getattr(user, "pk", None) else None,
    )
    apply_upload(reversal, user)
    return reversal
