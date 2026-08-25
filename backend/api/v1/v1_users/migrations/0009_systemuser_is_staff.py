from django.db import migrations, models


def grant_staff_to_superusers(apps, schema_editor):
    """PA-6 D-13: is_staff was a property returning is_superuser.

    Making it a real field would otherwise lock every current superuser out
    of the Django admin, because the new column defaults to False.
    """
    SystemUser = apps.get_model("v1_users", "SystemUser")
    SystemUser.objects.filter(is_superuser=True).update(is_staff=True)


def revoke_staff(apps, schema_editor):
    """Reverse is a no-op on data: dropping the column discards it anyway."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        (
            "v1_users",
            "0008_systemuser_administration_systemuser_station_name_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="systemuser",
            name="is_staff",
            field=models.BooleanField(
                default=False,
                help_text="Can sign in to the Django admin site.",
            ),
        ),
        migrations.RunPython(grant_staff_to_superusers, revoke_staff),
    ]
