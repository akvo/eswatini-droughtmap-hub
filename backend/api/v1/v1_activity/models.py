from django.db import models

from utils.soft_deletes_model import SoftDeletes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_activity.constants import (
    ActivityStatus,
    ActivitySector,
    ActivityResponseType,
)
from api.v1.v1_activity.validators import validate_triggers


class ResponseActivity(SoftDeletes):
    code = models.CharField(max_length=50, unique=True)  # ACT-<SECTOR>-<seq>
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    sector = models.IntegerField(choices=ActivitySector.FieldStr.items())

    # Single generic trigger. Shape validated by validate_triggers:
    #   {"dclass": {"class": <1..5|null>, "months": <int>=1>},
    #    "vuln":   {"op": <TriggerOperator>, "value": <1..4>} | null,
    #    "exp":    [{"indicator": <EXPOSURE_INDICATORS>,
    #                "op": <TriggerOperator>, "value": num}, ...],
    #    "other":  str | null}
    triggers = models.JSONField(
        null=True, blank=True, validators=[validate_triggers])

    # Ownership (Step 3). No timing / geographic_scope (dropped per spec D-4).
    owner = models.CharField(max_length=255, null=True, blank=True)
    coord_with = models.CharField(max_length=255, null=True, blank=True)
    response_type = models.IntegerField(
        choices=ActivityResponseType.FieldStr.items(), null=True, blank=True)

    # Source (Step 4).
    source_doc = models.CharField(max_length=255, null=True, blank=True)
    # storage-relative path
    source_file = models.CharField(max_length=255, null=True, blank=True)
    # auto-bumped on activate
    version = models.CharField(max_length=20, default="v1.0")

    # Lifecycle.
    status = models.IntegerField(
        choices=ActivityStatus.FieldStr.items(), default=ActivityStatus.draft)
    created_by = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_activities")
    activated_by = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="activated_activities")
    # informational; gates nothing
    verified_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code}: {self.title}"

    class Meta:
        db_table = "response_activities"


class ActivitySignOff(models.Model):
    activity = models.ForeignKey(
        ResponseActivity, on_delete=models.CASCADE, related_name="signoffs")
    signed_by = models.ForeignKey(
        SystemUser, on_delete=models.SET_NULL, null=True,
        related_name="activity_signoffs")
    note = models.CharField(max_length=255, null=True, blank=True)
    recorded_by = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="activity_signoffs_recorded")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_signoffs"
        ordering = ["created_at"]


class ActivityHistory(models.Model):
    activity = models.ForeignKey(
        ResponseActivity, on_delete=models.CASCADE, related_name="history")
    from_status = models.IntegerField(
        choices=ActivityStatus.FieldStr.items(), null=True, blank=True)
    to_status = models.IntegerField(
        choices=ActivityStatus.FieldStr.items(), null=True, blank=True)
    user = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="activity_history")
    note = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_history"
        ordering = ["created_at"]
