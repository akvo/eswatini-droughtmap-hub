from types import SimpleNamespace
from django.test import TestCase, RequestFactory
from api.v1.v1_activity.permissions import CanManageActivity
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector
from api.v1.v1_users.constants import UserRoleTypes


def _user(role, sector=None):
    return SimpleNamespace(
        role=role, activity_sector=sector, is_authenticated=True)


class PermissionsTestCase(TestCase):
    def setUp(self):
        self.perm = CanManageActivity()
        self.rf = RequestFactory()

    def test_anonymous_denied(self):
        request = self.rf.get("/")
        request.user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(self.perm.has_permission(request, None))

    def test_reviewer_may_read(self):
        request = self.rf.get("/")
        request.user = _user(UserRoleTypes.reviewer, ActivitySector.wash)
        obj = SimpleNamespace(
            sector=ActivitySector.wash, status=ActivityStatus.draft)
        self.assertTrue(self.perm.has_permission(request, None))
        self.assertTrue(self.perm.has_object_permission(request, None, obj))

    def test_reviewer_cannot_edit_own_sector_draft(self):
        request = self.rf.patch("/")
        request.user = _user(UserRoleTypes.reviewer, ActivitySector.wash)
        obj = SimpleNamespace(
            sector=ActivitySector.wash, status=ActivityStatus.draft)
        self.assertFalse(self.perm.has_object_permission(request, None, obj))

    def test_reviewer_cannot_create(self):
        request = self.rf.post("/")
        request.user = _user(UserRoleTypes.reviewer, ActivitySector.wash)
        self.assertFalse(self.perm.has_permission(request, None))

    def test_reviewer_cannot_delete(self):
        request = self.rf.delete("/")
        request.user = _user(UserRoleTypes.reviewer, ActivitySector.wash)
        obj = SimpleNamespace(
            sector=ActivitySector.wash, status=ActivityStatus.draft)
        self.assertFalse(self.perm.has_object_permission(request, None, obj))

    def test_admin_can_delete(self):
        request = self.rf.delete("/")
        request.user = _user(UserRoleTypes.admin)
        obj = SimpleNamespace(
            sector=ActivitySector.wash, status=ActivityStatus.active)
        self.assertTrue(self.perm.has_object_permission(request, None, obj))
