from django.core.management.base import BaseCommand
from api.v1.v1_users.models import Ability, ActionEnum, UserRoleTypes


class Command(BaseCommand):
    help = "Seed the database with default roles and abilities."

    def handle(self, *args, **kwargs):
        # Define default roles and abilities
        default_data = [
            {
                "role": UserRoleTypes.admin,
                "abilities": [
                    {
                        "action": ActionEnum.CREATE.value,
                        "subject": "Publication"
                    },
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "Publication"
                    },
                    {
                        "action": ActionEnum.UPDATE.value,
                        "subject": "Publication"
                    },
                    {
                        "action": ActionEnum.DELETE.value,
                        "subject": "Publication"
                    },
                    {
                        "action": ActionEnum.CREATE.value,
                        "subject": "Review"
                    },
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "Review"
                    },
                    {
                        "action": ActionEnum.UPDATE.value,
                        "subject": "Review",
                        "conditions": {"owner": "true"},
                    },
                    {
                        "action": ActionEnum.DELETE.value,
                        "subject": "Review"
                    },
                ],
            },
            {
                "role": UserRoleTypes.reviewer,
                "abilities": [
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "Publication"
                    },
                    {
                        "action": ActionEnum.CREATE.value,
                        "subject": "Review"
                    },
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "Review",
                        "conditions": {"owner": "true"},
                    },
                    {
                        "action": ActionEnum.UPDATE.value,
                        "subject": "Review",
                        "conditions": {"owner": "true"},
                    },
                ],
            },
        ]

        # Seed roles and abilities
        for role_data in default_data:
            for ability_data in role_data["abilities"]:
                Ability.objects.get_or_create(
                    role=role_data["role"],
                    action=ability_data["action"],
                    subject=ability_data["subject"],
                    conditions=ability_data.get("conditions"),
                )

        self.stdout.write(
            self.style.SUCCESS("Successfully seeded roles and abilities.")
        )
