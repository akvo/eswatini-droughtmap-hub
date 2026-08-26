from django.db import migrations

GROUP_NAME = "Data operators"

# PA-6 D-13: the whole point of making is_staff a real field is that the
# operator reaches the DatasetUpload screen WITHOUT is_superuser. Without a
# group to grant, that is only achievable by hand-picking permissions in the
# admin, which is how least privilege quietly becomes "just tick superuser".
PERMISSIONS = ["add_datasetupload", "view_datasetupload"]


def create_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="v1_indicators", model="datasetupload"
    )
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    for codename in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={"name": f"Can {codename.split('_')[0]} dataset upload"},
        )
        group.permissions.add(permission)


def delete_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("v1_indicators", "0003_datasetupload"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(create_group, delete_group)]
