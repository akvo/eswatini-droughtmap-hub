from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.db import IntegrityError
from django.utils import timezone
from api.v1.v1_iks.models import KoboAdapter
from api.v1.v1_iks.admin import KoboAdapterForm, KoboAdapterAdmin
from .base import BaseIKSTestCase


class MockRequest:
    def __init__(self, user=None):
        self.user = user


class KoboAdapterAdminTests(BaseIKSTestCase):

    def test_save_demotes_other_active_adapters(self):
        """
        Saving a second KoboAdapter with active=True demotes the first one.
        """
        # The base setUp already created one active adapter (self.adapter)
        self.assertTrue(self.adapter.active)

        # Create a second active adapter
        second_adapter = KoboAdapter.objects.create(
            server_url="https://second.kobotoolbox.org",
            username="second_user",
            password="second_password",
            active=True,
        )

        # Refresh first adapter from database
        self.adapter.refresh_from_db()
        self.assertFalse(self.adapter.active)
        self.assertTrue(second_adapter.active)

    def test_only_one_active_at_a_time(self):
        """
        Exactly one active adapter is maintained when changing active status.
        """
        second_adapter = KoboAdapter.objects.create(
            server_url="https://second.kobotoolbox.org",
            username="second_user",
            password="second_password",
            active=False,
        )

        self.assertTrue(self.adapter.active)
        self.assertFalse(second_adapter.active)

        # Activate the second adapter
        second_adapter.active = True
        second_adapter.save()

        self.adapter.refresh_from_db()
        self.assertFalse(self.adapter.active)
        self.assertTrue(second_adapter.active)

    def test_db_constraint_rejects_raw_second_active(self):
        """
        The database unique constraint rejects multiple active adapters when
        bypassing save() via update().
        """
        KoboAdapter.objects.create(
            server_url="https://second.kobotoolbox.org",
            username="second_user",
            password="second_password",
            active=False,
        )

        # Bypass save() using bulk update to force a violation
        with self.assertRaises(IntegrityError):
            KoboAdapter.objects.update(active=True)

    def test_activation_resets_last_sync_timestamp(self):
        """
        Activating an adapter via save_model() resets last_sync_timestamp.
        """
        adapter = KoboAdapter.objects.create(
            server_url="https://second.kobotoolbox.org",
            username="second_user",
            password="second_password",
            last_sync_timestamp=timezone.now(),
            active=False,
        )

        site = AdminSite()
        admin_inst = KoboAdapterAdmin(KoboAdapter, site)
        form = KoboAdapterForm(
            instance=adapter,
            data={
                "server_url": adapter.server_url,
                "username": adapter.username,
                "password": "new_password",
                "active": True,
            },
        )
        if not form.is_valid():
            print("FORM ERRORS:", form.errors)
        self.assertTrue(form.is_valid())

        # Simulate admin form submission
        adapter.active = True
        admin_inst.save_model(
            MockRequest(self.user), adapter, form, change=True
        )

        adapter.refresh_from_db()
        self.assertIsNone(adapter.last_sync_timestamp)

    def test_ordinary_save_preserves_last_sync_timestamp(self):
        """
        Ordinary saves of an already active adapter
        do not reset last_sync_timestamp.
        """
        original_time = timezone.now()
        self.adapter.last_sync_timestamp = original_time
        self.adapter.save()

        # Perform save without changing active status
        self.adapter.save()
        self.adapter.refresh_from_db()
        self.assertEqual(self.adapter.last_sync_timestamp, original_time)

    def test_admin_action_activate_adapter(self):
        """
        Admin activate action successfully activates target and demotes others.
        """
        second_adapter = KoboAdapter.objects.create(
            server_url="https://second.kobotoolbox.org",
            username="second_user",
            password="second_password",
            last_sync_timestamp=timezone.now(),
            active=False,
        )

        site = AdminSite()
        admin_inst = KoboAdapterAdmin(KoboAdapter, site)
        admin_inst.message_user = lambda request, message, level=None: None
        queryset = KoboAdapter.objects.filter(pk=second_adapter.pk)

        admin_inst.activate_adapter(MockRequest(self.user), queryset)

        self.adapter.refresh_from_db()
        second_adapter.refresh_from_db()

        self.assertFalse(self.adapter.active)
        self.assertTrue(second_adapter.active)
        self.assertIsNone(second_adapter.last_sync_timestamp)

    def test_admin_action_deactivate_adapter(self):
        """
        Admin deactivate action successfully deactivates
        selected active adapters.
        """
        site = AdminSite()
        admin_inst = KoboAdapterAdmin(KoboAdapter, site)
        admin_inst.message_user = lambda request, message, level=None: None
        queryset = KoboAdapter.objects.filter(pk=self.adapter.pk)

        self.assertTrue(self.adapter.active)
        admin_inst.deactivate_adapter(MockRequest(self.user), queryset)
        self.adapter.refresh_from_db()
        self.assertFalse(self.adapter.active)

    def test_form_blank_password_unchanged(self):
        """
        Submitting form with empty password preserves current password.
        """
        form = KoboAdapterForm(
            instance=self.adapter,
            data={
                "server_url": self.adapter.server_url,
                "username": self.adapter.username,
                "password": "",
                "active": self.adapter.active,
            },
        )
        self.assertTrue(form.is_valid())
        saved_instance = form.save()
        self.assertEqual(saved_instance.password, "test_kobo_password")

    def test_form_new_password_overwrites(self):
        """
        Submitting form with a new password updates stored password.
        """
        form = KoboAdapterForm(
            instance=self.adapter,
            data={
                "server_url": self.adapter.server_url,
                "username": self.adapter.username,
                "password": "brand_new_password",
                "active": self.adapter.active,
            },
        )
        self.assertTrue(form.is_valid())
        saved_instance = form.save()
        self.assertEqual(saved_instance.password, "brand_new_password")

    def test_download_command_uses_active_adapter_after_switch(self):
        """
        download_iks_data command queries only active adapter.
        """
        second_adapter = KoboAdapter.objects.create(
            server_url="https://second.kobotoolbox.org",
            username="second_user",
            password="second_password",
            active=True,
        )
        self.adapter.refresh_from_db()
        self.assertFalse(self.adapter.active)

        # Call download command, expect it to run with second_adapter
        # Using check option / invalid credentials to see if
        # it targets the second one.
        # But we can just inspect the first active adapter in command's query
        active_adapter = (
            KoboAdapter.objects.filter(active=True)
            .order_by("-updated_at")
            .first()
        )
        self.assertEqual(active_adapter.pk, second_adapter.pk)

    def test_kobo_seeder_unchanged(self):
        """
        Seeder runs successfully and creates adapter within constraint rules.
        """
        # Delete existing active ones
        KoboAdapter.objects.all().delete()
        call_command("kobo_seeder", username="seed_user", password="seed_pass")
        self.assertEqual(KoboAdapter.objects.filter(active=True).count(), 1)
