from django.core.management.base import BaseCommand, CommandError

from api.v1.v1_weather.client import Wis2Client
from api.v1.v1_weather.models import WeatherSource
from api.v1.v1_weather.services import sync_stations


class Command(BaseCommand):
    help = "Sync the weather-station registry from the active WIS2 source."

    def handle(self, *args, **options):
        source = WeatherSource.objects.filter(is_active=True).first()
        if not source:
            raise CommandError(
                "No active WeatherSource configured "
                "(set WIS2_BASE_URL/WIS2_COLLECTION_ID or add one in admin)."
            )
        client = Wis2Client(source.base_url, source.collection_id)
        count = sync_stations(client, source)
        self.stdout.write(
            self.style.SUCCESS(f"Synced {count} stations from WIS2.")
        )
