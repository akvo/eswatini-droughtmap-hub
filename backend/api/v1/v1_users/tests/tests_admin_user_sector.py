from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from api.v1.v1_users.admin import SystemUserAdmin
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
