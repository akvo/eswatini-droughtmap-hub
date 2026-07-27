from django.core.management.base import BaseCommand

from api.v1.v1_weather.citizen_science import dispatch_cs_reminders


class Command(BaseCommand):
    help = (
        "Queue citizen-science reminder emails for every active observer "
        "still missing last month's reading. Cron: 1st of month, 07:00."
    )

    def handle(self, *args, **options):
        count = dispatch_cs_reminders()
        self.stdout.write(f"Dispatched {count} reminder(s)")
