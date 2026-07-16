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
