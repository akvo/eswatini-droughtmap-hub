from django.contrib.admin.sites import AdminSite
from django.test import Client, TestCase

from api.v1.v1_activity.constants import ActivitySector
from api.v1.v1_users.admin import SystemUserAdmin
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser


def _fieldset_field_names(fieldsets):
    """Flatten a Django admin fieldsets tuple into a flat set of field names."""
    names = set()
    for _label, opts in fieldsets:
        names.update(opts.get("fields", ()))
    return names


class SystemUserAdminExposureTestCase(TestCase):
    def setUp(self):
        self.admin = SystemUserAdmin(SystemUser, AdminSite())

    def test_activity_sector_in_list_display_and_filter(self):
        self.assertIn("activity_sector", self.admin.list_display)
        self.assertIn("activity_sector", self.admin.list_filter)

    def test_activity_sector_in_edit_and_add_forms(self):
        self.assertIn(
            "activity_sector", _fieldset_field_names(self.admin.fieldsets)
        )
        self.assertIn(
            "activity_sector", _fieldset_field_names(self.admin.add_fieldsets)
        )

    def test_technical_working_group_in_list_and_edit_form(self):
        self.assertIn("technical_working_group", self.admin.list_display)
        self.assertIn("technical_working_group", self.admin.list_filter)
        self.assertIn(
            "technical_working_group",
            _fieldset_field_names(self.admin.fieldsets),
        )

    def test_edit_null_twg_user_saves_activity_sector(self):
        """A NULL-TWG reviewer can be assigned a sector via the admin edit
        form without being forced to pick a technical_working_group."""
        superuser = SystemUser.objects.create(
            email="su@test.org", name="su",
            role=UserRoleTypes.admin, is_superuser=True, email_verified=True,
        )
        superuser.set_password("Test1234")
        superuser.save()
        reviewer = SystemUser.objects.create(
            email="lead@test.org", name="lead",
            role=UserRoleTypes.reviewer, email_verified=True,
            technical_working_group=None, activity_sector=None,
        )
        client = Client()
        client.force_login(superuser)
        resp = client.post(
            "/admin/v1_users/systemuser/%d/change/" % reviewer.pk,
            {
                "email": reviewer.email,
                "name": reviewer.name,
                "role": str(UserRoleTypes.reviewer),
                "activity_sector": str(ActivitySector.food),
                "technical_working_group": "",  # left blank
                "email_verified": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)  # saved + redirect
        reviewer.refresh_from_db()
        self.assertEqual(reviewer.activity_sector, ActivitySector.food)
        self.assertIsNone(reviewer.technical_working_group)
