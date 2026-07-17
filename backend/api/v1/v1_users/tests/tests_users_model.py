from django.test import TestCase
from django.core.exceptions import ValidationError
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.constants import ActivitySector


class UserModelTestCase(TestCase):
    def setUp(self):
        self.user = SystemUser.objects._create_user(
            email="test@test.org", password="Test1234", name="test"
        )

    def test_get_sign_pk(self):
        self.assertTrue(self.user.get_sign_pk)

    def test_soft_delete_user(self):
        self.user.soft_delete()
        self.assertIsNotNone(self.user.id)
        self.assertTrue(self.user.deleted_at)

    def test_restore_deleted_user(self):
        self.user.restore()
        self.assertIsNone(self.user.deleted_at)

    def test_hard_delete_user(self):
        self.user.delete(hard=True)
        total_users = SystemUser.objects.count()
        self.assertEqual(total_users, 0)

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError) as context:
            SystemUser.objects._create_user(
                email=None,
                password="test1234",
                name="test",
            )
        self.assertEqual(
            str(context.exception),
            "The given email must be set"
        )

    def test_successfully_created_superuser(self):
        admin = SystemUser.objects.create_superuser(
            email="admin@mail.com",
            password="admin",
            name="admin"
        )
        self.assertIsNotNone(admin.id)
        total_admin = SystemUser.objects.filter(
            is_superuser=True,
            email_verified=False
        ).count()
        self.assertEqual(total_admin, 1)

    def test_create_admin_without_is_superuser(self):
        with self.assertRaises(ValueError) as context:
            SystemUser.objects.create_superuser(
                email="admin@mail.com",
                password="admin",
                name="admin",
                role=UserRoleTypes.reviewer
            )
        self.assertEqual(
            str(context.exception),
            "Invalid Admin role"
        )

    def _clean_sector(self, value):
        field = SystemUser._meta.get_field("activity_sector")
        return field.clean(value, self.user)

    def test_activity_sector_accepts_valid_sector(self):
        self.assertEqual(self._clean_sector(ActivitySector.food), 1)  # no raise

    def test_activity_sector_accepts_none(self):
        self.assertIsNone(self._clean_sector(None))  # blank/null allowed

    def test_activity_sector_rejects_out_of_range(self):
        with self.assertRaises(ValidationError):
            self._clean_sector(99)
