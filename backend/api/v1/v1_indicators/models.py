from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from api.v1.v1_publication.models import Administration
from api.v1.v1_users.models import SystemUser
from api.v1.v1_indicators.constants import UploadOrigin, UploadStatus


class Indicator(models.Model):
    administration = models.OneToOneField(
        Administration,
        on_delete=models.CASCADE,
        related_name="indicator",
        db_column="administration_id",
    )

    # ---
    # Risk exposure sub-indicators (raw inputs; normalisation derived per cycle)
    # ---
    land_use_dvi_agri = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    population = models.PositiveIntegerField(null=True, blank=True)
    cattle = models.PositiveIntegerField(null=True, blank=True)
    water_demand = models.FloatField(null=True, blank=True)

    # --- Vulnerability input (single national IPC layer; V value derived via rescale) ---
    ipc_phase = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    # --- Eligibility filters (NOT risk inputs; referenced by SOP triggers) ---
    under_five = models.PositiveIntegerField(default=0)
    elderly = models.PositiveIntegerField(default=0)
    rainfed_cropland = models.PositiveIntegerField(default=0)
    rangeland = models.PositiveIntegerField(default=0)
    boreholes = models.PositiveIntegerField(default=0)
    taps = models.PositiveIntegerField(default=0)

    # --- Provenance ---
    source = models.CharField(max_length=255, default="placeholder")
    as_of = models.DateField(null=True, blank=True)
    is_placeholder = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "indicator"
        constraints = [
            models.UniqueConstraint(
                fields=["administration"],
                name="uniq_indicator_per_administration",
            ),
            models.CheckConstraint(
                check=models.Q(land_use_dvi_agri__isnull=True)
                | (
                    models.Q(land_use_dvi_agri__gte=0.0)
                    & models.Q(land_use_dvi_agri__lte=1.0)
                ),
                name="ck_indicator_dvi_agri_unit",
            ),
            models.CheckConstraint(
                check=models.Q(ipc_phase__isnull=True)
                | (models.Q(ipc_phase__gte=1) & models.Q(ipc_phase__lte=5)),
                name="ck_indicator_ipc_phase_range",
            ),
        ]


class DatasetUpload(models.Model):
    """One operator-submitted file for one registered dataset (PA-6).

    Doubles as the audit trail and the provenance record: the file that
    produced a value stays on the storage volume, checksummed, next to the
    declared source and vintage, so "where did this number come from" is
    answerable without asking anyone.

    A multi-dataset file (D-15) yields one row per recognised value column,
    all sharing the same `file`, `checksum`, `source_label` and `as_of`.
    Grouping in the changelist is by `checksum` — same bytes, same upload —
    so no batch column exists for the purpose.
    """

    dataset = models.CharField(max_length=64, db_index=True)
    origin = models.CharField(max_length=16, default=UploadOrigin.upload)
    file = models.FileField(upload_to="datasets/%Y/%m/")
    checksum = models.CharField(max_length=64, db_index=True)
    source_label = models.CharField(max_length=255)
    as_of = models.DateField()
    status = models.PositiveSmallIntegerField(
        choices=UploadStatus.FieldStr.items(),
        default=UploadStatus.validated,
    )
    report = models.JSONField(default=dict)
    geonode_id = models.IntegerField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        SystemUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dataset_uploads",
    )
    applied_by = models.ForeignKey(
        SystemUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_dataset_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.dataset} @ {self.as_of} ({self.status_label})"

    @property
    def status_label(self):
        return UploadStatus.FieldStr.get(self.status, "unknown")

    @property
    def definition(self):
        """The DatasetDef this row writes, or None if the slug is unknown.

        Nullable on purpose: a registry entry can be removed while historical
        rows that used it remain, and the changelist must still render them.
        """
        from api.v1.v1_indicators.datasets import DATASETS

        return DATASETS.get(self.dataset)

    @property
    def indicator_source(self):
        """What lands in `Indicator.source` when this upload is applied."""
        stamp = self.as_of
        if hasattr(stamp, "strftime"):
            stamp = stamp.strftime("%Y-%m")
        else:
            stamp = str(stamp)[:7]
        return f"{self.source_label} ({stamp})"

    @property
    def changed_count(self):
        return len(
            [
                row
                for row in self.report.get("diff", [])
                if row.get("before") != row.get("after")
            ]
        )

    class Meta:
        db_table = "dataset_uploads"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["dataset", "-created_at"])]
