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
    population = models.PositiveIntegerField(default=0)
    under_five = models.PositiveIntegerField(default=0)
    cropland_ha = models.PositiveIntegerField(default=0)
    rainfed_share = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    livestock = models.PositiveIntegerField(default=0)
    rangeland = models.PositiveIntegerField(default=0)
    boreholes = models.PositiveIntegerField(default=0)
    taps = models.PositiveIntegerField(default=0)
    v_ipc = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    v_prep = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
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
                check=models.Q(rainfed_share__gte=0.0)
                & models.Q(rainfed_share__lte=1.0),
                name="ck_indicator_rainfed_share_unit",
            ),
            models.CheckConstraint(
                check=models.Q(v_ipc__gte=0.0)
                & models.Q(v_ipc__lte=1.0)
                & models.Q(v_prep__gte=0.0)
                & models.Q(v_prep__lte=1.0),
                name="ck_indicator_vuln_unit",
            ),
        ]
