from django.db import models
from django.core.exceptions import ValidationError
from utils.soft_deletes_model import SoftDeletes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.constants import (
    PublicationStatus,
    AdministrationZones,
    RasterIndicatorTypes,
    VALIDATABLE_CATEGORIES,
)


class Administration(models.Model):
    name = models.CharField(max_length=100, null=False)
    region = models.CharField(max_length=50, null=True, blank=True)
    zone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=AdministrationZones.choices(),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "administrations"


def validate_json_values(json_values: list = []):
    if not isinstance(json_values, list):
        raise ValidationError("JSON values must be a list of objects.")
    for item in json_values:  # pragma: no cover
        if not isinstance(item, dict):
            raise ValidationError("Each item in JSON must be a dictionary.")
        if "administration_id" not in item:
            raise ValidationError(
                "Each item must contain an 'administration_id' key."
            )
        # if "value" not in item:
        #     raise ValidationError(
        #         "Each item must contain a 'value' key."
        #     )


class Publication(SoftDeletes):
    year_month = models.DateField(null=False)
    cdi_geonode_id = models.IntegerField(null=False, unique=True)
    initial_values = models.JSONField(
        null=False, validators=[validate_json_values]
    )
    validated_values = models.JSONField(
        null=True, blank=True, validators=[validate_json_values]
    )
    due_date = models.DateField(null=False)
    status = models.IntegerField(
        choices=PublicationStatus.FieldStr.items(),
        default=PublicationStatus.in_review,
        null=True,
    )
    narrative = models.TextField(null=True, blank=True)
    bulletin_url = models.URLField(max_length=255, null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"Publication: {self.cdi_geonode_id} - "
            f"{self.year_month.strftime('%Y-%m')}"
        )

    @property
    def completed_reviews(self):
        return self.reviews.filter(
            is_completed=True,
            completed_at__isnull=False,
        )

    class Meta:
        db_table = "publications"


class Review(models.Model):
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(SystemUser, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    suggestion_values = models.JSONField(
        null=True, blank=True, validators=[validate_json_values]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_overdue_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"Review: {self.publication.year_month} by {self.user.email}"

    class Meta:
        db_table = "reviews"


class ValidationDecision(models.Model):
    """One NDRMA validation decision per (publication, Inkhundla).

    Created as a draft on first save and promoted in place on submit.
    `Publication.validated_values` stays the *published projection* of the
    submitted rows: it is what the map, the exports and the National Overview
    read, so this table is purely additive and nothing downstream changes.

    This table is authoritative for history and audit; validated_values is
    authoritative for what is published. They agree whenever the decision
    endpoint is the writer.
    """

    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="validation_decisions",
    )
    administration = models.ForeignKey(
        Administration,
        on_delete=models.CASCADE,
        related_name="validation_decisions",
    )
    # Null only while a draft has no pick yet.
    category = models.IntegerField(
        choices=VALIDATABLE_CATEGORIES, null=True, blank=True
    )
    reasoning = models.TextField(null=True, blank=True)
    is_draft = models.BooleanField(default=True)

    # Snapshot of the reviewer majority at submit time — never recomputed.
    # Recomputing would let a late review flip a historical decision from
    # "accepted" to "overridden", rewriting an audit record after the fact.
    majority_category = models.IntegerField(null=True, blank=True)
    is_override = models.BooleanField(default=False)

    validated_by = models.ForeignKey(
        SystemUser, on_delete=models.SET_NULL, null=True, blank=True
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"ValidationDecision: {self.publication_id}"
            f"/{self.administration_id}"
        )

    class Meta:
        db_table = "validation_decisions"
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "administration"],
                name="uniq_validation_decision_per_inkhundla",
            )
        ]


class PublicationRaster(models.Model):
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="rasters"
    )
    indicator = models.CharField(
        max_length=10, choices=RasterIndicatorTypes.choices()
    )
    geonode_id = models.IntegerField()
    values = models.JSONField(
        null=True, blank=True, validators=[validate_json_values]
    )
    extracted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.publication_id}:{self.indicator}"

    class Meta:
        db_table = "publication_rasters"
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "indicator"],
                name="uniq_publication_raster_indicator",
            )
        ]


class PublicationGeonode(models.Model):
    """Cached GeoNode resource metadata — the geodata the publication
    list/detail needs, so reads survive GeoNode downtime (D-1/D-2).

    One row per GeoNode raster resource. Refreshed by two writers only:
      - the CDI pipeline push (POST /geonode/publications, steady state)
      - the sync_publication_geonodes backfill command (history / recovery)
    The read path (CDIGeonodeAPI.get) never calls GeoNode at all.
    """

    geonode_id = models.IntegerField(unique=True)
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    # resource `date` stored as first-of-month
    year_month = models.DateField()
    subtype = models.CharField(max_length=20, default="raster")
    detail_url = models.URLField(max_length=512, null=True, blank=True)
    embed_url = models.URLField(max_length=512, null=True, blank=True)
    thumbnail_url = models.URLField(max_length=512, null=True, blank=True)
    download_url = models.URLField(max_length=512, null=True, blank=True)
    # bytes; frontend formats as e.g. "200 KB"
    file_size = models.BigIntegerField(null=True, blank=True)
    # GeoNode resource `created` datetime
    resource_created = models.DateTimeField(null=True, blank=True)
    # full GeoNode payload kept for forward-compatibility
    raw = models.JSONField(null=True, blank=True)
    # auto-updated on every cache write
    synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PublicationGeonode:{self.geonode_id} ({self.year_month})"

    class Meta:
        db_table = "publication_geonodes"
        indexes = [models.Index(fields=["category", "year_month"])]
