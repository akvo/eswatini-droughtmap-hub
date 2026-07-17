from django import forms
from django.contrib import admin
from django.core.management import call_command
from django_q.tasks import async_task
from .models import KoboAdapter, KoboForm


def reset_form_cursors():
    """D-5: a newly activated adapter is a different Kobo server, so what we
    have already pulled says nothing about what it holds. Clearing every
    form's cursor makes the next sync re-pull each form in full.

    The cursor lives on KoboForm (the sync is per form), so an adapter switch
    resets all of them rather than one field on the adapter.
    """
    return KoboForm.objects.update(last_sync_timestamp=None)


class KoboAdapterForm(forms.ModelForm):
    """
    Custom form that:
    - Renders `password` as a masked PasswordInput (not readable text).
    - On edit, leaves `password` blank by default; only overwrites when
      a new value is typed.
    """

    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Leave blank to keep the existing password.",
    )

    class Meta:
        model = KoboAdapter
        fields = "__all__"

    def _post_clean(self):
        super()._post_clean()
        if self.cleaned_data.get("active"):
            if hasattr(self, "_errors") and "__all__" in self._errors:
                non_field_errors = self._errors["__all__"]
                filtered_errors = []
                for err in non_field_errors:
                    err_msg = str(err)
                    if (
                        "one_active_kobo_adapter" not in err_msg
                        and "already exists" not in err_msg
                    ):
                        filtered_errors.append(err)
                if filtered_errors:
                    self._errors["__all__"] = self.error_class(filtered_errors)
                else:
                    del self._errors["__all__"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_password = self.cleaned_data.get("password")
        if not new_password:
            # Reload the stored password from the DB (blank = unchanged)
            if instance.pk:
                instance.password = KoboAdapter.objects.get(
                    pk=instance.pk
                ).password
        else:
            instance.password = new_password
        if commit:
            instance.save()
        return instance


@admin.register(KoboAdapter)
class KoboAdapterAdmin(admin.ModelAdmin):
    form = KoboAdapterForm
    list_display = (
        "server_url",
        "username",
        "active",
        "updated_at",
    )
    list_filter = ("active",)
    search_fields = ("server_url", "username")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-active", "-updated_at")
    actions = ["activate_adapter", "deactivate_adapter"]

    fieldsets = (
        (
            None,
            {
                "fields": ("server_url", "username", "password", "active"),
            },
        ),
        (
            "Sync Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        Detect False→True activation transition and reset the sync cursors.
        The demotion of other active adapters happens inside
        obj.save() (model).
        """
        was_active = False
        if obj.pk:
            was_active = (
                KoboAdapter.objects.filter(pk=obj.pk)
                .values_list("active", flat=True)
                .first()
                or False
            )

        activating = obj.active and not was_active
        super().save_model(request, obj, form, change)
        if activating:
            reset_form_cursors()

    @admin.action(description="Set selected adapter as active")
    def activate_adapter(self, request, queryset):
        """
        One-click switch from the list page.
        Only acts on the first selected adapter; warns if multiple selected.
        """
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one adapter to activate.",
                level="warning",
            )
            return
        adapter = queryset.first()
        if adapter.active:
            self.message_user(
                request,
                f"{adapter.server_url} is already active.",
            )
            return
        adapter.active = True
        adapter.save()  # triggers KoboAdapter.save() → atomic demotion
        reset_form_cursors()  # D-5: re-pull every form against the new server
        self.message_user(
            request,
            f"{adapter.server_url} is now the active adapter. "
            "Sync cursors have been reset; every form will be re-pulled "
            "on the next sync.",
        )

    @admin.action(description="Set selected adapters as inactive")
    def deactivate_adapter(self, request, queryset):
        """
        Deactivate selected adapters.
        """
        count = queryset.update(active=False)
        self.message_user(
            request, f"Successfully deactivated {count} adapter(s)."
        )


@admin.register(KoboForm)
class KoboFormAdmin(admin.ModelAdmin):
    """
    Admin panel for managing Kobo Forms (IKS).

    Operators can register multiple forms (e.g. a dummy/testing form and the
    real/production form). The download_iks_data command iterates ALL
    registered forms, so adding or removing a form here controls which data
    is pulled on the next sync — no code deploy required.
    """

    list_display = (
        "uuid",
        "name",
        "active",
        "last_sync_timestamp",
        "description",
        "created_at",
        "updated_at",
    )
    list_filter = ("active",)
    search_fields = ("uuid", "name")
    readonly_fields = (
        "questions",
        "options",
        "languages",
        "last_sync_timestamp",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    fieldsets = (
        (
            None,
            {
                "fields": ("uuid", "name", "active", "description"),
            },
        ),
        (
            "Sync Metadata (read-only)",
            {
                "fields": (
                    "questions",
                    "options",
                    "languages",
                    "last_sync_timestamp",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        `uuid` is editable on add (so operators can self-serve without CLI).
        On change it becomes readonly to prevent breaking existing
        KoboData FK references.
        """
        if obj:  # editing an existing record
            return ("uuid",) + self.readonly_fields
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """
        Queue a sync as soon as an active form has never been pulled — on add,
        and after an adapter switch clears the cursors. Without this the form
        is live in the API but empty until the next scheduled run.
        """
        super().save_model(request, obj, form, change)
        if obj.active and obj.last_sync_timestamp is None:
            async_task(call_command, "download_iks_data")
            self.message_user(
                request,
                f"Sync queued for '{obj.name}'. Data appears once the "
                "worker finishes; reload this page to check.",
            )

    def delete_model(self, request, obj):
        """
        Cascade-aware delete: count related KoboData rows before deletion and
        surface a warning so the operator understands the data impact.
        """
        count = obj.data.count()
        super().delete_model(request, obj)
        self.message_user(
            request,
            f"Form '{obj.name}' deleted. "
            f"{count} KoboData row(s) were also removed.",
            level="warning" if count > 0 else "success",
        )

    actions = ["activate_forms", "deactivate_forms"]

    @admin.action(description="Mark selected forms as active")
    def activate_forms(self, request, queryset):
        count = queryset.update(active=True)
        self.message_user(
            request, f"Successfully activated {count} Kobo Form(s)."
        )

    @admin.action(description="Mark selected forms as inactive")
    def deactivate_forms(self, request, queryset):
        count = queryset.update(active=False)
        self.message_user(
            request, f"Successfully deactivated {count} Kobo Form(s)."
        )
