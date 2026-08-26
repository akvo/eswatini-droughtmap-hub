from django.test import TestCase, override_settings
from django.core.management import call_command
from api.v1.v1_users.models import Ability, UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=False)
class AbilitiesTestCase(TestCase):
    def test_activity_abilities_seeded(self):
        call_command("generate_roles_n_abilities_seeder")
        admin_actions = set(Ability.objects.filter(
            role=UserRoleTypes.admin, subject="Activity"
        ).values_list("action", flat=True))
        self.assertEqual(admin_actions, {"create", "read", "update", "delete"})
        reviewer_actions = set(Ability.objects.filter(
            role=UserRoleTypes.reviewer, subject="Activity"
        ).values_list("action", flat=True))
        self.assertEqual(reviewer_actions, {"read"})
