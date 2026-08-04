from django.core import signing
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_jobs.constants import JobTypes
from api.v1.v1_jobs.models import Jobs
from api.v1.v1_publication.models import Administration
from api.v1.v1_users.admin import SystemUserCreationForm
from api.v1.v1_users.constants import CS_LINK_SALT, UserRoleTypes
from api.v1.v1_users.models import SystemUser
from eswatini.settings import WEBDOMAIN
from utils.email_helper import EmailTypes, email_context


@override_settings(USE_TZ=False, TEST_ENV=True)
class ObserverMagicLinkTests(APITestCase):
    def setUp(self):
        cache.clear()  # CSLinkThrottle state
        self.administration = Administration.objects.create(
            pk=111, name="Hhukwini", region="Hhohho"
        )
        self.observer = SystemUser.objects._create_user(
            email="sipho@example.sz",
            password="unused",
            name="Sipho",
            role=UserRoleTypes.observer,
            administration=self.administration,
            station_name="Hhukwini Community",
        )
        self.reviewer = SystemUser.objects._create_user(
            email="reviewer@example.com", password="pass", name="Rev"
        )

    def request_link(self, email):
        return self.client.post(
            reverse("observer-request-link", kwargs={"version": "v1"}),
            {"email": email},
        )

    def verify(self, token):
        return self.client.post(
            reverse("observer-verify-link", kwargs={"version": "v1"}),
            {"token": token},
        )

    def token_for(self, user):
        return signing.dumps(user.pk, salt=CS_LINK_SALT)

    def test_request_link_observer_dispatches_job(self):
        response = self.request_link(self.observer.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 1
        )

    def test_request_link_unknown_email_same_response_no_job(self):
        response = self.request_link("nobody@example.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        known = self.request_link(self.observer.email)
        # Identical body whether or not the email exists (no enumeration)
        self.assertEqual(response.json(), known.json())
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 1
        )

    def test_request_link_non_observer_role_no_job(self):
        response = self.request_link(self.reviewer.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Jobs.objects.filter(type=JobTypes.cs_magic_link).count(), 0
        )

    def test_verify_link_returns_jwt_and_verifies_email(self):
        response = self.verify(self.token_for(self.observer))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["role"], UserRoleTypes.observer)
        self.assertEqual(data["user"]["station_name"], "Hhukwini Community")
        self.assertIn("AUTH_TOKEN", response.cookies)
        self.observer.refresh_from_db()
        self.assertTrue(self.observer.email_verified)

    def test_verify_link_rejects_tampered_token(self):
        bad = signing.dumps(self.observer.pk, salt="other-salt")
        response = self.verify(bad)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_link_rejects_non_observer(self):
        response = self.verify(self.token_for(self.reviewer))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_link_rejects_soft_deleted_observer(self):
        token = self.token_for(self.observer)
        self.observer.soft_delete()
        response = self.verify(token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_throttle_limits_link_requests(self):
        for _ in range(10):
            self.assertEqual(
                self.request_link("nobody@example.com").status_code,
                status.HTTP_200_OK,
            )
        response = self.request_link("nobody@example.com")
        self.assertEqual(
            response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )

    def test_one_active_observer_per_administration(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SystemUser.objects._create_user(
                    email="second@example.sz",
                    password="unused",
                    name="Second",
                    role=UserRoleTypes.observer,
                    administration=self.administration,
                )

    def test_admin_creation_form_blank_password_is_unusable(self):
        form = SystemUserCreationForm(data={"email": "obs2@example.sz"})
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save(commit=False)
        self.assertFalse(user.has_usable_password())

    def test_admin_creation_form_keeps_provided_password(self):
        form = SystemUserCreationForm(
            data={
                "email": "staff@example.com",
                "password1": "Sup3rSecret!",
                "password2": "Sup3rSecret!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save(commit=False)
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("Sup3rSecret!"))

    def test_magic_link_cta_points_at_the_frontend_route(self):
        # WEBDOMAIN is the frontend origin and the observer app lives at
        # /citizen-weather. /citizen-science is the backend API prefix and
        # 404s in Next.js, which silently breaks every sign-in email.
        for email_type in (EmailTypes.cs_magic_link, EmailTypes.cs_reminder):
            context = email_context(
                {
                    "name": "Sipho",
                    "station_name": "Hhukwini Community",
                    "month_label": "May 2026",
                    "token": "tok3n",
                },
                type=email_type,
            )
            self.assertEqual(
                context["cta_url"],
                "{0}/citizen-weather?token=tok3n".format(WEBDOMAIN),
            )

    def test_constraint_ignores_non_observers_and_deleted(self):
        # Reviewers with NULL administration are unlimited
        SystemUser.objects._create_user(
            email="another-reviewer@example.com", password="p", name="R2"
        )
        # Soft-deleting the observer frees the Inkhundla slot
        self.observer.soft_delete()
        replacement = SystemUser.objects._create_user(
            email="replacement@example.sz",
            password="unused",
            name="Replacement",
            role=UserRoleTypes.observer,
            administration=self.administration,
        )
        self.assertIsNotNone(replacement.pk)
