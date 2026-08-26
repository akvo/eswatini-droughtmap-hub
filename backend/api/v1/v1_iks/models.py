from django.db import models, transaction
from django.db.models import Q, UniqueConstraint
from api.v1.v1_publication.models import Administration


class KoboAdapter(models.Model):
    server_url = models.URLField(max_length=255)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=128)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.active:
                KoboAdapter.objects.exclude(pk=self.pk).filter(
                    active=True
                ).update(active=False)
            super().save(*args, **kwargs)

    def validate_constraints(self, exclude=None):
        if self.active:
            exclude = exclude or []
            if "one_active_kobo_adapter" not in exclude:
                # Use list copy to avoid modifying external exclude parameter
                exclude = list(exclude) + ["one_active_kobo_adapter"]
        super().validate_constraints(exclude=exclude)

    class Meta:
        db_table = "kobo_adapters"
        constraints = [
            UniqueConstraint(
                fields=["active"],
                condition=Q(active=True),
                name="one_active_kobo_adapter",
            ),
        ]


class KoboForm(models.Model):
    uuid = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    questions = models.JSONField(default=dict)
    options = models.JSONField(default=dict)
    languages = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "kobo_forms"


class KoboData(models.Model):
    form = models.ForeignKey(
        KoboForm, on_delete=models.CASCADE, related_name="data"
    )
    kobo_id = models.BigIntegerField(unique=True)
    geo = models.JSONField(null=True, blank=True)
    submission_time = models.DateTimeField()
    submitted_by = models.CharField(max_length=150, null=True, blank=True)
    instance_name = models.CharField(max_length=255, null=True, blank=True)
    raw_data = models.JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "kobo_data"


class IKSIndicator(models.Model):
    SECTION_B = "B"
    SECTION_C = "C"
    SECTION_D = "D"
    SECTION_CHOICES = [
        (SECTION_B, "Section B – Rainfall Predictors"),
        (SECTION_C, "Section C – Seasonal/Extreme Weather"),
        (SECTION_D, "Section D – Soil/Vegetation"),
    ]

    kobo_form = models.ForeignKey(
        KoboForm, on_delete=models.CASCADE, related_name="indicators"
    )
    name = models.CharField(max_length=255)
    section = models.CharField(
        max_length=1,
        choices=SECTION_CHOICES,
        blank=True,
        default="",
        db_index=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iks_indicators"


class IKSValue(models.Model):
    kobo_id = models.BigIntegerField()
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE, related_name="iks_values"
    )
    iks_indicator = models.ForeignKey(
        IKSIndicator, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iks_values"
