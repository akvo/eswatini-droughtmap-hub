from django.core.management import call_command
from django.core.management.base import CommandError
from api.v1.v1_iks.models import KoboAdapter, KoboForm
from .base import BaseIKSTestCase


class KoboSeederCommandTests(BaseIKSTestCase):

    def test_kobo_seeder(self):
        """
        Test that the seeder command executes cleanly and creates objects.
        """
        # Clean existing to ensure creation
        KoboAdapter.objects.all().delete()
        KoboForm.objects.all().delete()

        call_command(
            "kobo_seeder", username="seed_user", password="seed_pass"
        )
        self.assertTrue(KoboAdapter.objects.filter(active=True).exists())
        self.assertTrue(
            KoboForm.objects.filter(uuid="a3ytas3GLhSewNTZByCCsd").exists()
        )

    def test_kobo_seeder_with_form_uid(self):
        """Test the seeder honors the --form-uid argument."""
        KoboForm.objects.all().delete()

        call_command(
            "kobo_seeder",
            form_uid="custom-form-uid",
            username="seed_user",
            password="seed_pass",
        )
        self.assertTrue(
            KoboForm.objects.filter(uuid="custom-form-uid").exists()
        )
        self.assertFalse(
            KoboForm.objects.filter(uuid="a3ytas3GLhSewNTZByCCsd").exists()
        )

    def test_kobo_seeder_empty_form_uid_uses_default(self):
        """Test that an empty --form-uid falls back to the default UUID."""
        KoboForm.objects.all().delete()

        call_command(
            "kobo_seeder",
            form_uid="",
            username="seed_user",
            password="seed_pass",
        )
        self.assertTrue(
            KoboForm.objects.filter(uuid="a3ytas3GLhSewNTZByCCsd").exists()
        )

    def test_kobo_seeder_requires_credentials(self):
        """Test the seeder errors when username/password are missing."""
        with self.assertRaises(CommandError):
            call_command("kobo_seeder")
