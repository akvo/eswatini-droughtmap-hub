from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib import admin
from django_q.tasks import async_task
from django_json_widget.widgets import JSONEditorWidget
from .models import SystemUser, Ability
from api.v1.v1_jobs.models import Jobs, JobTypes, JobStatus
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_weather.citizen_science import dispatch_cs_magic_link


class SystemUserCreationForm(UserCreationForm):
    """Passwords optional: observers are passwordless (magic-link only),
    and admins/reviewers set theirs via the welcome email anyway. A blank
    password saves an UNUSABLE one — never a usable hash of ''."""

    class Meta(UserCreationForm.Meta):
        model = SystemUser
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("password1", "password2"):
            self.fields[field].required = False
        self.fields["password1"].help_text = (
            "Leave blank for observers — they sign in via emailed "
            "magic link, never a password."
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        if not self.cleaned_data.get("password1"):
            user.set_unusable_password()
        if commit:
            user.save()
        return user


# Add manage users in admin django
class SystemUserAdmin(UserAdmin):
    site_header = "Manage Users"
    model = SystemUser
    add_form = SystemUserCreationForm
    list_display = (
        "email",
        "name",
        "role",
        "email_verified",
        "activity_sector",
        "technical_working_group",
        "manages_citizen_science",
    )
    list_filter = (
        "role",
        "email_verified",
        "activity_sector",
        "technical_working_group",
        # CS-DEL-1: makes "who holds this grant?" answerable from the
        # changelist rather than by querying the database.
        "manages_citizen_science",
    )
    fieldsets = (
        (None, {"fields": ("email", "name", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "email_verified",
                    "activity_sector",
                    "technical_working_group",
                    # CS-DEL-1. Sits with the other grants, NOT in the
                    # "Citizen science (observer role only)" group below —
                    # those are an observer's own station fields, not a
                    # permission.
                    "manages_citizen_science",
                )
            },
        ),
        (
            "Citizen science (observer role only)",
            {
                "fields": (
                    "administration",
                    "station_name",
                    "station_sensors",
                    "station_type",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                    "role",
                    "technical_working_group",
                    "activity_sector",
                    "administration",
                    "station_name",
                    "station_sensors",
                    "station_type",
                ),
            },
        ),
    )
    search_fields = (
        "email",
        "name",
    )
    ordering = ("email",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            if obj.role == UserRoleTypes.observer:
                # Observers are passwordless: their welcome IS the magic
                # link (WX-6 D-3), not the password-setup email below.
                dispatch_cs_magic_link(obj)
                return
            obj.generate_reset_password_code()
            if int(request.POST.get("role")[0]) == UserRoleTypes.admin:
                # Automatically set superuser status for admin role
                obj.is_superuser = True
                obj.save(update_fields=["is_superuser"])
            job = Jobs.objects.create(
                type=JobTypes.new_user_password_setup,
                status=JobStatus.on_progress,
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_reset_password",
                obj,
                True,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            job.task_id = task_id
            job.save()


class AbilityForm(forms.ModelForm):
    class Meta:
        model = Ability
        fields = "__all__"
        widgets = {
            "conditions": JSONEditorWidget,
        }


class AbilityAdmin(admin.ModelAdmin):
    site_header = "Manage Permissions"
    model = Ability
    form = AbilityForm

    list_display = ("role", "action", "subject", "conditions")
    list_filter = ("role", "action", "subject")
    fieldsets = (
        (None, {"fields": ("role", "action", "subject", "conditions")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("role", "action", "subject", "conditions"),
            },
        ),
    )
    search_fields = ("action", "subject")
    ordering = ("role",)


admin.site.register(SystemUser, SystemUserAdmin)
admin.site.register(Ability, AbilityAdmin)
