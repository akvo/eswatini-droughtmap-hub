"""Operator surface for dataset uploads (PA-6 D-1).

Django admin rather than a Next.js screen: the interaction is a changelist,
a four-field add form, a read-only detail and an action with a confirmation
page — which is what Django admin already is.
"""

import csv

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from rest_framework.exceptions import ValidationError

from api.v1.v1_indicators import uploads
from api.v1.v1_indicators.constants import UploadStatus
from api.v1.v1_indicators.datasets import DATASETS, KEY_COLUMNS
from api.v1.v1_indicators.models import DatasetUpload
from api.v1.v1_publication.models import Administration

# Excel reads a leading =, +, - or @ as a formula. Inkhundla names flow into
# the template we generate, so they are escaped on the way out.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

STATUS_COLOURS = {
    UploadStatus.rejected: "#b3261e",
    UploadStatus.validated: "#8a6100",
    UploadStatus.applied: "#1e6b34",
    UploadStatus.superseded: "#5f6368",
    UploadStatus.discarded: "#5f6368",
}


def _escape_cell(value):
    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in FORMULA_PREFIXES else text


class DatasetUploadForm(forms.ModelForm):
    """Three inputs. The header declares the dataset, so there is no
    dataset field to pick wrongly (D-15)."""

    file = forms.FileField(
        label="CSV file",
        help_text=mark_safe(
            'Fill only the columns you have. '
            '<a href="../template.csv"><strong>Download the blank '
            'template</strong></a> — it lists all 59 Tinkhundla.'
        ),
    )
    as_of = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="The period the data describes, not the day you got it.",
    )
    source_label = forms.CharField(
        max_length=255,
        help_text="Which organisation and which export, e.g. "
                  "'DWA/JRBA abstraction permit registry'.",
    )

    class Meta:
        model = DatasetUpload
        fields = ["file", "source_label", "as_of"]

    def clean_file(self):
        """Reject here, not in save_model.

        A DRF ValidationError escaping save_model renders a 500 page, which
        is the opposite of D-2's requirement that the rejection tell the
        operator what to do. Raised as a form error, it comes back on the
        field with the instruction attached.
        """
        uploaded = self.cleaned_data["file"]
        try:
            uploads.validate_extension(uploaded)
        except ValidationError as error:
            detail = error.detail
            if isinstance(detail, (list, tuple)):
                detail = detail[0]
            raise forms.ValidationError(str(detail))
        return uploaded


@admin.register(DatasetUpload)
class DatasetUploadAdmin(admin.ModelAdmin):
    form = DatasetUploadForm
    list_display = (
        "dataset", "as_of", "source_label", "status_pill",
        "changed_count", "uploaded_by", "created_at",
    )
    list_filter = ("dataset", "status", "origin")
    search_fields = ("source_label", "checksum")
    date_hierarchy = "created_at"
    actions = ["apply_selected", "discard_selected", "revert_selected"]
    change_list_template = "admin/v1_indicators/datasetupload/change_list.html"
    readonly_fields = (
        "dataset", "origin", "checksum", "status_pill", "uploaded_by",
        "applied_by", "applied_at", "created_at", "download_link",
        "report_table",
    )

    def get_fields(self, request, obj=None):
        if obj is None:
            return ["file", "source_label", "as_of"]
        return [
            "dataset", "source_label", "as_of", "status_pill",
            "download_link", "origin", "checksum", "uploaded_by",
            "applied_by", "applied_at", "created_at", "report_table",
        ]

    def has_change_permission(self, request, obj=None):
        # An upload is the record of an event, never edited after the fact.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # --- display -------------------------------------------------------

    @admin.display(description="status", ordering="status")
    def status_pill(self, obj):
        return format_html(
            '<b style="color:{}">{}</b>',
            STATUS_COLOURS.get(obj.status, "#000"),
            obj.status_label,
        )

    @admin.display(description="changed")
    def changed_count(self, obj):
        return obj.changed_count

    @admin.display(description="file")
    def download_link(self, obj):
        if not obj.pk or not obj.file:
            return "—"
        url = reverse(
            "admin:v1_indicators_datasetupload_download", args=[obj.pk]
        )
        return format_html('<a href="{}">Download original</a>', url)

    @admin.display(description="report")
    def report_table(self, obj):
        return mark_safe(_render_report(obj))

    # --- routes --------------------------------------------------------

    def get_urls(self):
        meta = self.model._meta
        return [
            path(
                "template.csv",
                self.admin_site.admin_view(self.template_csv),
                name=f"{meta.app_label}_{meta.model_name}_template",
            ),
            path(
                "<int:pk>/download/",
                self.admin_site.admin_view(self.download),
                name=f"{meta.app_label}_{meta.model_name}_download",
            ),
        ] + super().get_urls()

    def template_csv(self, request):
        """Generated per request from the live administrations table.

        A committed static file would go stale the moment an Inkhundla is
        renamed, and then fail at match time with no obvious cause.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="dih_data_template.csv"'
        )
        writer = csv.writer(response)
        columns = [d.field for d in DATASETS.values()]
        writer.writerow(list(KEY_COLUMNS) + columns)
        rows = Administration.objects.order_by("region", "name").values_list(
            "id", "name", "region"
        )
        for adm_id, name, region in rows:
            writer.writerow(
                [adm_id, _escape_cell(name), _escape_cell(region)]
                + [""] * len(columns)
            )
        return response

    def download(self, request, pk):
        upload = self.get_object(request, pk)
        if upload is None or not upload.file:
            self.message_user(request, "File not found.", messages.ERROR)
            return HttpResponse(status=404)
        upload.file.open("rb")
        response = HttpResponse(upload.file.read(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{upload.file.name.split("/")[-1]}"'
        )
        return response

    # --- create --------------------------------------------------------

    def save_model(self, request, obj, form, change):
        """Parse, validate and store — one row per recognised column.

        Deliberately writes nothing to Indicator (D-3).
        """
        created = uploads.create_uploads(
            uploaded=form.cleaned_data["file"],
            source_label=form.cleaned_data["source_label"],
            as_of=form.cleaned_data["as_of"],
            user=request.user,
        )
        obj.pk = created[0].pk
        rejected = [u for u in created if u.status == UploadStatus.rejected]
        ok = [u for u in created if u.status == UploadStatus.validated]

        if ok:
            self.message_user(
                request,
                f"Validated: {', '.join(u.dataset for u in ok)}. "
                "Nothing is saved yet — select the row(s) and run "
                "'Apply selected uploads' to review the changes.",
                messages.SUCCESS,
            )
        for upload in rejected:
            detail = upload.report.get("errors", [{}])[0].get("detail", "")
            self.message_user(
                request,
                f"Rejected ({upload.dataset}): "
                f"{upload.report.get('error_total', 1)} problem(s). {detail}",
                messages.ERROR,
            )
        for upload in created:
            for warning in upload.report.get("warnings", []):
                if warning.get("code") == "ignored_columns":
                    # D-16: loud, because a typo fails exactly like a new
                    # field would.
                    self.message_user(
                        request, warning["detail"], messages.WARNING
                    )

    # --- actions -------------------------------------------------------

    @admin.action(description="Apply selected uploads")
    def apply_selected(self, request, queryset):
        pending = queryset.filter(status=UploadStatus.validated)
        if not pending:
            self.message_user(
                request,
                "Nothing to apply — only validated uploads can be applied.",
                messages.WARNING,
            )
            return None

        if request.POST.get("confirmed"):
            for upload in pending:
                try:
                    result = uploads.apply_upload(upload, request.user)
                except ValidationError as error:
                    self.message_user(
                        request, f"{upload.dataset}: {error.detail}",
                        messages.ERROR,
                    )
                    continue
                self.message_user(
                    request,
                    f"{upload.dataset}: {result.written} written, "
                    f"{result.skipped} unchanged. Source recorded as "
                    f"'{upload.indicator_source}'.",
                    messages.SUCCESS,
                )
            return None

        # The acceptance gate (D-3): the full before/after, before anything
        # is true.
        return render(
            request,
            "admin/v1_indicators/datasetupload/apply_confirmation.html",
            {
                "title": "Confirm these changes",
                "uploads": [
                    {"upload": u, "report": mark_safe(_render_report(u))}
                    for u in pending
                ],
                "queryset": pending,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )

    @admin.action(description="Discard selected uploads")
    def discard_selected(self, request, queryset):
        updated = queryset.filter(status=UploadStatus.validated).update(
            status=UploadStatus.discarded
        )
        self.message_user(request, f"{updated} upload(s) discarded.")

    @admin.action(description="Revert selected applied uploads")
    def revert_selected(self, request, queryset):
        for upload in queryset.filter(status=UploadStatus.applied):
            try:
                reversal = uploads.revert_upload(upload, request.user)
            except ValidationError as error:
                self.message_user(
                    request, f"{upload.dataset}: {error.detail}",
                    messages.ERROR,
                )
                continue
            self.message_user(
                request,
                f"{upload.dataset}: reverted to the previous values "
                f"(recorded as upload #{reversal.pk}).",
                messages.SUCCESS,
            )


def _render_report(obj) -> str:
    report = obj.report or {}
    parts = []

    counts = format_html_join(
        " · ", "{}: <b>{}</b>",
        (
            (key, report.get(key))
            for key in ("rows_read", "matched", "blank", "error_total")
            if report.get(key) is not None
        ),
    )
    if counts:
        parts.append(f"<p>{counts}</p>")

    for warning in report.get("warnings", []):
        parts.append(
            format_html(
                '<p style="color:#8a6100">⚠ {}</p>', warning.get("detail", "")
            )
        )

    errors = report.get("errors", [])
    if errors:
        rows = format_html_join(
            "", "<tr><td>{}</td><td>{}</td><td>{}</td></tr>",
            ((e.get("row", "—"), e.get("code", ""), e.get("detail", ""))
             for e in errors),
        )
        parts.append(
            '<table><thead><tr><th>row</th><th>code</th><th>problem</th>'
            f"</tr></thead><tbody>{rows}</tbody></table>"
        )

    diff = report.get("diff", [])
    if diff:
        rows = format_html_join(
            "",
            "<tr><td>{}</td><td>{}</td><td>{}</td></tr>",
            (
                (
                    row.get("name", ""),
                    "—" if row.get("before") is None else row["before"],
                    "—" if row.get("after") is None else row["after"],
                )
                for row in diff
            ),
        )
        parts.append(
            "<table><thead><tr><th>Inkhundla</th><th>before</th>"
            f"<th>after</th></tr></thead><tbody>{rows}</tbody></table>"
        )
    return "".join(parts) or "<p>No report.</p>"
