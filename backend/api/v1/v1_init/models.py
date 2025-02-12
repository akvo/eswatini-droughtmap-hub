from django.db import models


class Settings(models.Model):
    ts_emails = models.JSONField(
        null=True,
        blank=True
    )
    secret_key = models.CharField(
        max_length=255,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "settings"
