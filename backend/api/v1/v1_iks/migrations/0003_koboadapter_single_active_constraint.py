from django.db import migrations, models


def collapse_multi_active(apps, schema_editor):
    """
    Pre-constraint data migration: keep only the most-recently-updated
    active adapter; demote all others. Safe to re-run (idempotent).
    """
    KoboAdapter = apps.get_model("v1_iks", "KoboAdapter")
    actives = list(
        KoboAdapter.objects.filter(active=True).order_by("-updated_at")
    )
    # Demote all except the first (newest)
    for extra in actives[1:]:
        extra.active = False
        extra.save(update_fields=["active"])


class Migration(migrations.Migration):

    dependencies = [
        ("v1_iks", "0002_iksindicator_section"),
    ]

    operations = [
        migrations.RunPython(collapse_multi_active, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="koboadapter",
            constraint=models.UniqueConstraint(
                condition=models.Q(active=True),
                fields=["active"],
                name="one_active_kobo_adapter",
            ),
        ),
    ]
