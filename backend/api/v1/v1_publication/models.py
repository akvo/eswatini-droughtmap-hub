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
    # Equal-area (EPSG:6933) area of the eswatini.topojson polygon, computed
    # once by generate_administrations_seeder. Stored rather than derived per
    # request so the web process never imports the geo stack (BB-3 D-1).
    # Nullable: an unseeded row omits the brief header's km2, never shows 0.
    area_km2 = models.FloatField(null=True, blank=True)
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
    # Set by the demo seeders on every row THEY create, and by nothing else.
    # `cdi_geonode_id` used to carry this meaning through a reserved id range,
    # which forced seeded rows off the real GeoNode assets and left the CDI
    # publication list unable to join them (DEMO-1 D-2).
    is_seeded = models.BooleanField(default=False)
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
    # resource `date`, normalised to first-of-month by save()
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

    def save(self, *args, **kwargs):
        # Every reader looks this row up by month — `cached_geonode_id`, which
        # binds a publication to its asset, and `cached_component_resource`,
        # which attaches the component rasters — and both ask for
        # `year_month=<YYYY-MM>-01`. GeoNode's resource `date` is a full date,
        # so a resource dated the 31st was stored as the 31st and no lookup
        # ever found it: 2 of 317 cached CDI rows, silently unattachable.
        # Normalising on the way in fixes all three writers at once (the
        # pipeline push, sync_publication_geonodes, the seeder) instead of
        # teaching every reader to match a range.
        # to_python, not isinstance juggling: callers hand this field a date
        # or an ISO string interchangeably, and the field already knows how to
        # read both.
        year_month = self._meta.get_field("year_month").to_python(
            self.year_month
        )
        if year_month and year_month.day != 1:
            self.year_month = year_month.replace(day=1)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"PublicationGeonode:{self.geonode_id} ({self.year_month})"

    class Meta:
        db_table = "publication_geonodes"
        indexes = [models.Index(fields=["category", "year_month"])]


class BriefForwardLog(models.Model):
    """Immutable audit record for every "Forward brief" send."""

    sender = models.ForeignKey(
        "v1_users.SystemUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="brief_forwards",
    )
    recipients_payload = models.JSONField(
        help_text="List of {email, name} dicts actually emailed."
    )
    inkhundla_id = models.IntegerField(
        help_text="administration PK at time of send."
    )
    inkhundla_name = models.CharField(max_length=120)
    components = models.JSONField(
        help_text="List of component key strings included in the brief."
    )
    brief_url = models.TextField(
        help_text="The /brief-builder?... URL embedded in the email body."
    )
    note = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brief_forward_logs"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"BriefForward by {self.sender_id} at {self.sent_at:%Y-%m-%d %H:%M}"  # noqa
