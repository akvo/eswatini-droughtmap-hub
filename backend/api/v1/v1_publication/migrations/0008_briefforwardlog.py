from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("v1_publication", "0007_alter_administration_zone"),
    ]

    operations = [
        migrations.CreateModel(
            name="BriefForwardLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "recipients_payload",
                    models.JSONField(
                        help_text="List of {email, name} dicts actually emailed."
                    ),
                ),
                (
                    "inkhundla_id",
                    models.IntegerField(
                        help_text="administration PK at time of send."
                    ),
                ),
                ("inkhundla_name", models.CharField(max_length=120)),
                (
                    "components",
                    models.JSONField(
                        help_text="List of component key strings included in the brief."
                    ),
                ),
                (
                    "brief_url",
                    models.TextField(
                        help_text="The /brief-builder?... URL embedded in the email body."
                    ),
                ),
                ("note", models.TextField(blank=True, default="")),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                (
                    "sender",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="brief_forwards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "brief_forward_logs",
                "ordering": ["-sent_at"],
            },
        ),
    ]
