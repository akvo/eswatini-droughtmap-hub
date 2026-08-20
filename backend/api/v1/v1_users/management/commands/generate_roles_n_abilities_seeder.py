from django.core.management.base import BaseCommand
from django.conf import settings
from api.v1.v1_users.models import Ability, ActionEnum, UserRoleTypes


class Command(BaseCommand):
    help = "Seed the database with default roles and abilities."

    def add_arguments(self, parser):
        parser.add_argument(
            "-t",
            "--test",
            nargs="?",
            const=False,
            default=False,
            type=bool,
        )

    def handle(self, *args, **options):
        test = options.get("test")
        # Define default roles and abilities
        default_data = [
            {
                "role": UserRoleTypes.admin,
                "abilities": [
                    {
                        "action": ActionEnum.CREATE.value,
                        "subject": "Publication",
                    },
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "Publication",
                    },
                    {
                        "action": ActionEnum.UPDATE.value,
                        "subject": "Publication",
                    },
                    {
                        "action": ActionEnum.DELETE.value,
                        "subject": "Publication",
                    },
                    {"action": ActionEnum.CREATE.value, "subject": "Review"},
                    {"action": ActionEnum.READ.value, "subject": "Review"},
                    {
                        "action": ActionEnum.UPDATE.value,
                        "subject": "Review",
                        "conditions": {"owner": "true"},
                    },
                    {"action": ActionEnum.DELETE.value, "subject": "Review"},
                    {"action": ActionEnum.CREATE.value, "subject": "Activity"},
                    {"action": ActionEnum.READ.value, "subject": "Activity"},
                    {"action": ActionEnum.UPDATE.value, "subject": "Activity"},
                    {"action": ActionEnum.DELETE.value, "subject": "Activity"},
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "CitizenScience",
                    },
                    {
                        "action": ActionEnum.CREATE.value,
                        "subject": "CitizenScience",
                    },
                    {
                        "action": ActionEnum.UPDATE.value,
                        "subject": "CitizenScience",
                    },
                ],
            },
            {
                "role": UserRoleTypes.reviewer,
                "abilities": [
                    {
                        "action": ActionEnum.READ.value,
                        "subject": "Publication",
                    },
                    {"action": ActionEnum.CREATE.value, "subject": "Review"},
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
                    # Reviewers get the Activity Library read-only: they
                    # consult SOPs while reviewing, they do not author them.
                    {"action": ActionEnum.READ.value, "subject": "Activity"},
                ],
            },
        ]

        if test:
            default_data = [
                {
                    "role": UserRoleTypes.admin,
                    "abilities": [
                        {"action": ActionEnum.CREATE.value, "subject": "TEST"}
                    ],
                }
            ]
        # Seed roles and abilities
        seeded = []
        for role_data in default_data:
            for ability_data in role_data["abilities"]:
                ability, _ = Ability.objects.update_or_create(
                    role=role_data["role"],
                    action=ability_data["action"],
                    subject=ability_data["subject"],
                    defaults={"conditions": ability_data.get("conditions")},
                )
                seeded.append(ability.pk)

        # default_data is the whole truth, not a set of additions. Without
        # this, an ability dropped from the list above lives on forever in
        # every environment already seeded — a revoked permission that keeps
        # working.
        Ability.objects.exclude(pk__in=seeded).delete()

        if not settings.TEST_ENV:
            self.stdout.write(  # pragma: no cover
                self.style.SUCCESS("Successfully seeded roles and abilities.")
            )
