from django.core.management.base import BaseCommand
from api.v1.v1_iks.models import KoboAdapter, KoboForm


class Command(BaseCommand):
    help = "Seeds default Kobo adapter credentials and IKS forms"

    def handle(self, *args, **options):
        # Seed default Kobo Adapter
        adapter, created = KoboAdapter.objects.get_or_create(
            server_url="https://kf.kobotoolbox.org",
            defaults={
                "username": "default_user",
                "password": "default_password",
                "active": True,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS("Created default Kobo Adapter.")
            )
        else:
            self.stdout.write("Default Kobo Adapter already exists.")

        # Seed default Kobo Form
        form, created = KoboForm.objects.get_or_create(
            uuid="a3ytas3GLhSewNTZByCCsd",
            defaults={
                "name": "CDI-E - IKS by Akvo",
                "description": "Indigenous Knowledge Systems observations form.",  # noqa
                "questions": {},
                "options": {},
                "languages": ["en"],
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created default Kobo Form."))
        else:
            self.stdout.write("Default Kobo Form already exists.")
