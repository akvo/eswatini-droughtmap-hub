from django.core.management.base import BaseCommand
from api.v1.v1_iks.models import KoboAdapter, KoboForm

KOBO_FORM_UUID = "a3ytas3GLhSewNTZByCCsd"


class Command(BaseCommand):
    help = "Seeds default Kobo adapter credentials and IKS forms"

    def add_arguments(self, parser):
        parser.add_argument(
            "--form-uid",
            type=str,
            default="",
            help="Kobo form UID (defaults to KOBO_FORM_UUID if empty)",
        )
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help="Kobo adapter username",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Kobo adapter password",
        )

    def handle(self, *args, **options):
        form_uid = options.get("form_uid") or KOBO_FORM_UUID

        # Seed default Kobo Adapter
        adapter, created = KoboAdapter.objects.get_or_create(
            server_url="https://kf.kobotoolbox.org",
            defaults={
                "username": options["username"],
                "password": options["password"],
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
            uuid=form_uid,
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
