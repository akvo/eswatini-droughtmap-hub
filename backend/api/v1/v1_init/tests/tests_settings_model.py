from django.test import TestCase
from api.v1.v1_init.models import Settings


class SettingsModelTest(TestCase):

    def test_create_settings_entry(self):
        """Test creating a Settings instance and checking attributes"""
        settings = Settings.objects.create(
            secret_key="test_secret_key",
            ts_emails=["tsc1@mail.com", "tsc2@mail.com"]
        )

        self.assertEqual(settings.secret_key, "test_secret_key")
        self.assertIsNotNone(settings.created_at)
        self.assertIsNone(settings.updated_at)
        self.assertEqual(len(settings.ts_emails), 2)

    def test_secret_key_uniqueness(self):
        """Test that secret keys must be unique"""
        Settings.objects.create(secret_key="unique_key")

        with self.assertRaises(Exception):  # IntegrityError expected
            Settings.objects.create(secret_key="unique_key")
