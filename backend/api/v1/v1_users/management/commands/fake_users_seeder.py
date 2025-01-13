import random
from django.core.management import BaseCommand
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import (
    UserRoleTypes,
    TechnicalWorkingGroup
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--repeat",
            nargs="?",
            const=3,
            default=3,
            type=int
        )
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool
        )

    def handle(self, *args, **options):
        test = options.get("test")
        repeat = options.get("repeat")

        for _ in range(repeat):
            total_users = SystemUser.objects.exclude(
                role=UserRoleTypes.admin
            ).count()
            index = total_users + 1
            twg = random.choice(list(
                TechnicalWorkingGroup.FieldStr.keys()
            ))
            SystemUser.objects._create_user(
                email=f"reviewer{index}@mail.com",
                password="Changeme123",
                name=f"Reviewer {index}",
                technical_working_group=twg
            )
        if not test:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{repeat} users have been created successfully."
                )
            )  # pragma: no cover
