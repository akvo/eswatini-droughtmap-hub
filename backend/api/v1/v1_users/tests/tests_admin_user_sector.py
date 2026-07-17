from django.test import Client, TestCase

from api.v1.v1_activity.constants import ActivitySector
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser


class SystemUserAdminExposureTestCase(TestCase):
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
