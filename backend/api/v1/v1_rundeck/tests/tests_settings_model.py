from django.test import TestCase
from api.v1.v1_rundeck.models import Settings


class SettingsModelTest(TestCase):

    def test_create_settings_entry(self):
        """Test creating a Settings instance and checking attributes"""
        settings = Settings.objects.create(
            project_name="eswatini",
            job_id="34afdb08-3089-4c9c-9cc3-89c148110d5d",
            on_failure_emails=["tsc1@mail.com", "tsc2@mail.com"]
        )

        self.assertEqual(
            settings.job_id,
            "34afdb08-3089-4c9c-9cc3-89c148110d5d"
        )
        self.assertIsNotNone(settings.created_at)
        self.assertIsNone(settings.updated_at)
        self.assertEqual(len(settings.on_failure_emails), 2)

    def test_job_id_uniqueness(self):
        """Test that secret keys must be unique"""
        Settings.objects.create(
            project_name="eswatini",
            job_id="unique_key"
        )

        with self.assertRaises(Exception):  # IntegrityError expected
            Settings.objects.create(job_id="unique_key")
