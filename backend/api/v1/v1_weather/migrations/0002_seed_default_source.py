from django.conf import settings
from django.db import migrations


def seed_default_source(apps, schema_editor):
    """Seed the default WeatherSource from env (WIS2_BASE_URL +
    WIS2_COLLECTION_ID). The real host is internal — never committed."""
    base_url = getattr(settings, "WIS2_BASE_URL", None)
    collection_id = getattr(settings, "WIS2_COLLECTION_ID", None)
    if not base_url or not collection_id:
        return
    WeatherSource = apps.get_model("v1_weather", "WeatherSource")
    if WeatherSource.objects.exists():
        return
    WeatherSource.objects.create(
        base_url=base_url,
        collection_id=collection_id,
        is_active=True,
    )


def remove_default_source(apps, schema_editor):
    WeatherSource = apps.get_model("v1_weather", "WeatherSource")
    WeatherSource.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("v1_weather", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_source, remove_default_source),
    ]
