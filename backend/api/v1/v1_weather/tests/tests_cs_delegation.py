"""Delegated citizen-science management (CS-DEL-1).

The network is coordinated from UNESWA, not NDMA. `manages_citizen_science`
grants that one surface without the `admin` role, which would also carry
publications, settings and validation.

Every test here pairs the coordinator with `plain_reviewer` — identical but
for the flag. Without that control a passing suite cannot tell "the flag
granted this" from "reviewers could always do it".
"""
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_users.constants import TechnicalWorkingGroup, UserRoleTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.serializers import UserSerializer

HHUKWINI_ADM = 4588078


@override_settings(USE_TZ=False, TEST_ENV=True)
class CitizenScienceDelegationTests(APITestCase):
    def setUp(self):
        # Abilities are seeded, not fixtures: this suite asserts what a
        # session carries, and an empty ability table would make every
        # subject assertion below pass vacuously.
        call_command("generate_roles_n_abilities_seeder")
        self.hhukwini = Administration.objects.create(
            pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho"
        )
        # The real configuration (D-2): a TWG reviewer who ALSO runs the
        # citizen-science network. A dedicated role could not express this,
        # because `role` is single-valued.
        self.coordinator = SystemUser.objects._create_user(
            email="coordinator@example.sz",
            password="pass",
            name="CS Coordinator",
            role=UserRoleTypes.reviewer,
            technical_working_group=TechnicalWorkingGroup.uneswa,
        )
        self.coordinator.manages_citizen_science = True
        self.coordinator.save()

        # The control: same role, same TWG, no flag.
        self.plain_reviewer = SystemUser.objects._create_user(
            email="reviewer@example.sz",
            password="pass",
            name="Plain Reviewer",
            role=UserRoleTypes.reviewer,
            technical_working_group=TechnicalWorkingGroup.uneswa,
        )
        self.admin_user = SystemUser.objects.create_superuser(
            name="admin", email="admin@example.com", password="adminpass"
        )

    def url(self, name):
        return reverse(name, kwargs={"version": "v1"})

    # -- the grant --------------------------------------------------------

    def test_flag_defaults_to_false(self):
        """AC-10. Nobody holds the grant until an admin sets it."""
        self.assertFalse(self.plain_reviewer.manages_citizen_science)
        self.assertFalse(self.admin_user.manages_citizen_science)

    def test_coordinator_reaches_the_citizen_science_endpoints(self):
        """AC-1/AC-3, without the admin role."""
        self.client.force_authenticate(user=self.coordinator)
        for name in ("cs-stations", "cs-export"):
            with self.subTest(name=name):
                response = self.client.get(self.url(name))
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unflagged_reviewer_is_refused_at_the_api(self):
        """AC-9. Hiding the nav item is not a permission — the endpoint
        itself must refuse a reviewer who was never delegated."""
        self.client.force_authenticate(user=self.plain_reviewer)
        for method, name in (
            ("get", "cs-stations"),
            ("post", "cs-stations"),
            ("post", "cs-reminders"),
            ("get", "cs-export"),
        ):
            with self.subTest(method=method, name=name):
                response = getattr(self.client, method)(self.url(name))
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN
                )

    def test_admin_access_is_unchanged(self):
        """AC-5. The widening must not have moved anything for admins."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url("cs-stations"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -- the boundary -----------------------------------------------------

    def test_coordinator_is_still_refused_the_wis2_source(self):
        """AC-8 / D-4. WeatherSourceAPI shares IsAdmin with the endpoints
        above but is not part of this page — a search-and-replace on the
        permission class would have swept it up silently."""
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.get(self.url("weather-source"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_coordinator_cannot_mint_a_privileged_account(self):
        """AC-7, the escalation path. A station IS a user account, so this
        is the one endpoint where a non-admin creates one. The role is
        pinned server-side and a `role` in the body must be ignored."""
        self.client.force_authenticate(user=self.coordinator)

        response = self.client.post(
            self.url("cs-stations"),
            {
                "name": "Test Observer",
                "email": "observer@example.sz",
                "administration_id": self.hhukwini.pk,
                "station_name": "Test Station",
                "sensors": ["rain_gauge"],
                "send_welcome_email": False,
                "role": UserRoleTypes.admin,
                "manages_citizen_science": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = SystemUser.objects.get(email="observer@example.sz")
        self.assertEqual(created.role, UserRoleTypes.observer)
        self.assertFalse(created.manages_citizen_science)

    # -- how the grant reaches the frontend (D-5) -------------------------

    def test_coordinator_session_carries_citizen_science_abilities(self):
        """FR-6. The page's <Can I="read" a="CitizenScience"> guards render
        off the session's abilities, so the flag has to reach them."""
        abilities = UserSerializer(instance=self.coordinator).data[
            "abilities"
        ]
        subjects = {a["subject"] for a in abilities}
        self.assertIn("CitizenScience", subjects)

    def test_unflagged_reviewer_session_does_not(self):
        abilities = UserSerializer(instance=self.plain_reviewer).data[
            "abilities"
        ]
        subjects = {a["subject"] for a in abilities}
        self.assertNotIn("CitizenScience", subjects)

    def test_coordinator_keeps_every_reviewer_ability(self):
        """AC-11. The flag adds; it must never subtract. The coordinator
        holds a TWG seat and reviews drought maps as well."""
        reviewer_subjects = {
            (a["action"], a["subject"])
            for a in UserSerializer(instance=self.plain_reviewer).data[
                "abilities"
            ]
        }
        coordinator_subjects = {
            (a["action"], a["subject"])
            for a in UserSerializer(instance=self.coordinator).data[
                "abilities"
            ]
        }
        self.assertTrue(reviewer_subjects)
        self.assertTrue(reviewer_subjects.issubset(coordinator_subjects))
        self.assertEqual(
            self.coordinator.technical_working_group,
            TechnicalWorkingGroup.uneswa,
        )
