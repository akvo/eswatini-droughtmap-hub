from django.db import migrations, models
from django.db.models import Max


def carry_cursor_to_forms(apps, schema_editor):
    """Seed each form's cursor from the newest submission it already holds.

    The old cursor lived on the adapter and was the max across every form, so
    copying it onto forms as-is would drag quiet forms forward and skip their
    history. A form's own newest submission is what its cursor would have
    been; a form with no rows stays NULL so it back-fills in full.
    """
    KoboForm = apps.get_model("v1_iks", "KoboForm")
    for form in KoboForm.objects.all():
        newest = form.data.aggregate(Max("submission_time"))[
            "submission_time__max"
        ]
        if newest:
            form.last_sync_timestamp = newest
            form.save(update_fields=["last_sync_timestamp"])


def restore_cursor_to_adapter(apps, schema_editor):
    """Reverse: put the newest form cursor back on the active adapter."""
    KoboForm = apps.get_model("v1_iks", "KoboForm")
    KoboAdapter = apps.get_model("v1_iks", "KoboAdapter")
    newest = KoboForm.objects.aggregate(Max("last_sync_timestamp"))[
        "last_sync_timestamp__max"
    ]
    if newest:
        KoboAdapter.objects.filter(active=True).update(
            last_sync_timestamp=newest
        )


class Migration(migrations.Migration):

    dependencies = [
        ("v1_iks", "0004_koboform_active"),
    ]

    # Order matters: the new column must exist and be populated before the
    # old one is dropped, or the cursor is lost.
    operations = [
        migrations.AddField(
            model_name="koboform",
            name="last_sync_timestamp",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            carry_cursor_to_forms,
            restore_cursor_to_adapter,
        ),
        migrations.RemoveField(
            model_name="koboadapter",
            name="last_sync_timestamp",
        ),
    ]
