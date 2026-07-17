from unittest.mock import patch
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from api.v1.v1_iks.models import KoboData, KoboForm
from api.v1.v1_iks.admin import KoboFormAdmin
from .base import BaseIKSTestCase


class MockRequest:
    def __init__(self, user=None):
        self.user = user


class KoboFormAdminTests(BaseIKSTestCase):

    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.admin_inst = KoboFormAdmin(KoboForm, self.site)
        self.factory = RequestFactory()
        # Authenticate the test client as superuser for view-level tests
        self.client.force_login(self.user)

    # ------------------------------------------------------------------
    # T1: List view
    # ------------------------------------------------------------------
    def test_list_view_returns_200(self):
        """
        GET /admin/v1_iks/koboform/ returns HTTP 200 for a superuser.
        """
        response = self.client.get("/admin/v1_iks/koboform/")
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # T2: Add form via admin
    # ------------------------------------------------------------------
    def test_add_form_creates_koboform_row(self):
        """
        POSTing a new form to the admin add view creates a KoboForm row.
        """
        new_uuid = "dummyFormUID123456789"
        response = self.client.post(
            "/admin/v1_iks/koboform/add/",
            {
                "uuid": new_uuid,
                "name": "Clone of CDI-E - IKS (Dummy)",
                "description": "Testing form",
                "questions": "{}",
                "options": "{}",
                "languages": "[]",
            },
        )
        # Admin redirects to list on success (302)
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(KoboForm.objects.filter(uuid=new_uuid).exists())

    # ------------------------------------------------------------------
    # T3: Edit name — uuid stays unchanged
    # ------------------------------------------------------------------
    def test_edit_name_updates_name(self):
        """
        Editing a KoboForm's name via admin updates it; uuid is not changed.
        """
        original_uuid = self.form.uuid
        response = self.client.post(
            f"/admin/v1_iks/koboform/{self.form.pk}/change/",
            {
                "uuid": original_uuid,
                "name": "CDI-E - IKS (Updated Name)",
                "description": self.form.description or "",
                "questions": "{}",
                "options": "{}",
                "languages": "[]",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        self.form.refresh_from_db()
        self.assertEqual(self.form.name, "CDI-E - IKS (Updated Name)")
        self.assertEqual(self.form.uuid, original_uuid)

    # ------------------------------------------------------------------
    # T4: uuid is readonly on change, not on add
    # ------------------------------------------------------------------
    def test_uuid_readonly_on_change_not_on_add(self):
        """
        get_readonly_fields returns 'uuid' when an existing obj is passed,
        but not when obj=None (add view).
        """
        readonly_on_add = self.admin_inst.get_readonly_fields(
            MockRequest(self.user), obj=None
        )
        readonly_on_change = self.admin_inst.get_readonly_fields(
            MockRequest(self.user), obj=self.form
        )
        self.assertNotIn("uuid", readonly_on_add)
        self.assertIn("uuid", readonly_on_change)

    # ------------------------------------------------------------------
    # T5: Deleting a KoboForm cascades its KoboData rows
    # ------------------------------------------------------------------
    def test_delete_form_cascades_kobodata(self):
        """
        Deleting a KoboForm via delete_model removes its KoboData rows.
        """
        from django.utils import timezone

        kobodata = KoboData.objects.create(
            form=self.form,
            kobo_id=99991,
            submission_time=timezone.now(),
            raw_data={},
        )
        data_pk = kobodata.pk

        # Capture messages sent to user
        messages = []
        mock_request = MockRequest(self.user)
        self.admin_inst.message_user = (
            lambda req, msg, level=None: messages.append(msg)
        )

        self.admin_inst.delete_model(mock_request, self.form)

        # Form deleted
        self.assertFalse(KoboForm.objects.filter(pk=self.form.pk).exists())
        # KoboData cascaded
        self.assertFalse(KoboData.objects.filter(pk=data_pk).exists())
        # Warning message included cascade count
        self.assertTrue(len(messages) > 0)
        self.assertIn("1", messages[0])

    # ------------------------------------------------------------------
    # Adding an active form queues a sync so it is not live-but-empty
    # ------------------------------------------------------------------
    @patch("api.v1.v1_iks.admin.async_task")
    def test_saving_active_form_without_data_queues_sync(self, mock_async):
        new_form = KoboForm(
            uuid="a6JCtffpjhSSDXcZuZrfTv", name="CDI-E - IKS", active=True
        )
        mock_request = MockRequest(self.user)
        self.admin_inst.message_user = lambda req, msg, level=None: None

        self.admin_inst.save_model(mock_request, new_form, None, change=False)

        mock_async.assert_called_once()
        self.assertEqual(mock_async.call_args[0][1], "download_iks_data")

    @patch("api.v1.v1_iks.admin.async_task")
    def test_saving_inactive_form_does_not_queue_sync(self, mock_async):
        new_form = KoboForm(uuid="dormant-uid", name="Dormant", active=False)
        mock_request = MockRequest(self.user)

        self.admin_inst.save_model(mock_request, new_form, None, change=False)

        mock_async.assert_not_called()

    @patch("api.v1.v1_iks.admin.async_task")
    def test_saving_already_synced_form_does_not_queue_sync(self, mock_async):
        """Editing a form that carries a cursor must not re-trigger a pull."""
        from django.utils import timezone

        self.form.last_sync_timestamp = timezone.now()
        self.form.save()
        mock_request = MockRequest(self.user)

        self.admin_inst.save_model(mock_request, self.form, None, change=True)

        mock_async.assert_not_called()

    @patch("api.v1.v1_iks.admin.async_task")
    def test_saving_form_whose_cursor_was_reset_queues_sync(self, mock_async):
        """
        An adapter switch clears the cursors, so a form that still holds rows
        from the old server must re-pull against the new one.
        """
        from django.utils import timezone

        KoboData.objects.create(
            form=self.form,
            kobo_id=12345,
            submission_time=timezone.now(),
            raw_data={},
        )
        self.form.last_sync_timestamp = None
        self.form.save()
        self.admin_inst.message_user = lambda req, msg, level=None: None

        self.admin_inst.save_model(
            MockRequest(self.user), self.form, None, change=True
        )

        mock_async.assert_called_once()

    # ------------------------------------------------------------------
    # T6: Newly-added form is included in download_iks_data queryset
    # ------------------------------------------------------------------
    def test_new_form_included_in_download_queryset(self):
        """
        After adding an active second KoboForm, filter(active=True)
        returns both, confirming download_iks_data will sync it,
        but inactive forms are excluded.
        """
        self.assertTrue(
            self.form.active
        )  # Base form is active (True) by default

        # Create active form
        KoboForm.objects.create(
            uuid="prodFormUID987654321",
            name="CDI-E - IKS - Real/Production",
            description="Production IKS form",
            active=True,
        )
        # Create inactive form
        KoboForm.objects.create(
            uuid="inactiveFormUID98765",
            name="Inactive Form",
            description="Testing Inactive form",
            active=False,
        )

        all_active_forms = list(KoboForm.objects.filter(active=True))
        uuids = [f.uuid for f in all_active_forms]

        self.assertIn("a3ytas3GLhSewNTZByCCsd", uuids)
        self.assertIn("prodFormUID987654321", uuids)
        self.assertNotIn("inactiveFormUID98765", uuids)

    def test_bulk_activate_and_deactivate_forms(self):
        """
        Verify that activate_forms and deactivate_forms bulk actions
        correctly toggle the active field for selected forms.
        """
        form1 = KoboForm.objects.create(
            uuid="form1", name="Form 1", active=False
        )
        form2 = KoboForm.objects.create(
            uuid="form2", name="Form 2", active=False
        )

        queryset = KoboForm.objects.filter(uuid__in=["form1", "form2"])
        self.admin_inst.message_user = (
            lambda request, message, level=None: None
        )

        # Bulk Activate
        self.admin_inst.activate_forms(MockRequest(self.user), queryset)
        form1.refresh_from_db()
        form2.refresh_from_db()
        self.assertTrue(form1.active)
        self.assertTrue(form2.active)

        # Bulk Deactivate
        self.admin_inst.deactivate_forms(MockRequest(self.user), queryset)
        form1.refresh_from_db()
        form2.refresh_from_db()
        self.assertFalse(form1.active)
        self.assertFalse(form2.active)
