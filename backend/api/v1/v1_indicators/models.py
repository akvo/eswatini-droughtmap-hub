from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from api.v1.v1_publication.models import Administration


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
