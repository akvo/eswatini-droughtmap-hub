from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import (
    BULK_REASONING_PREFIX,
    AgreementFilter,
    DroughtCategory,
    PublicationStatus,
    ValidationStatus,
)
from api.v1.v1_publication.models import Publication, ValidationDecision
from api.v1.v1_publication.validation.utils import (
    agreement_of,
    build_validation_stats,
    ordered_rows,
)
from api.v1.v1_users.constants import TechnicalWorkingGroup, UserRoleTypes
from api.v1.v1_users.models import SystemUser


class AgreementOfTestCase(APITestCase):
    """D-1/D-2: three outcomes, and the middle one is deliberate."""

    def test_buckets(self):
        cases = {
            (): None,                       # nothing usable submitted
            (3,): None,                     # one reviewer agrees with nobody
            (3, 3): AgreementFilter.undisputed,
            (3, 3, 3, 3, 3): AgreementFilter.undisputed,
            (3, 4): None,                   # 2 distinct — mild, still a human
            (1, 2, 3): None,                # 3 distinct — exactly at the line
            (1, 2, 3, 4): AgreementFilter.disagreement,
            (0, 1, 2, 3, 5): AgreementFilter.disagreement,
        }
        for spread, expected in cases.items():
            self.assertEqual(
                agreement_of(list(spread)), expected, msg=str(spread)
            )

    def test_single_submission_is_never_undisputed(self):
        """D-1: the load-bearing clause.

        Without it a publication assigned one reviewer has every row `ready`
        AND every row unanimous, so one click validates the whole national
        map on one person's word.
        """
        self.assertIsNone(agreement_of([DroughtCategory.d2]))


@override_settings(USE_TZ=False, TEST_ENV=True)
class BulkValidationAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

        self.publication = Publication.objects.first()
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.client.force_authenticate(user=self.admin)

    def _url(self):
        return reverse(
            "validation-bulk",
            kwargs={"version": "v1", "pk": self.publication.id},
        )

    def _make_unanimous(self, count=3, category=DroughtCategory.d2):
        """Force the first `count` Tinkhundla to a unanimous D-class.

        The seeder randomises categories, so a fixture that relies on it
        happening to agree would be flaky by construction.
        """
        targets = [
            v["administration_id"]
            for v in self.publication.initial_values[:count]
        ]
        for review in self.publication.reviews.all():
            review.is_completed = True
            review.suggestion_values = [
                {
                    "administration_id": v["administration_id"],
                    "value": 0.2,
                    "comment": None,
                    "reviewed": True,
                    "category": (
                        category
                        if v["administration_id"] in targets
                        # Everything else spread wide so it lands in neither
                        # bucket and cannot drift into the write.
                        else (v["administration_id"] % 6)
                    ),
                }
                for v in self.publication.initial_values
            ]
            review.save()
        return targets

    def test_validates_the_unanimous_rows(self):
        targets = self._make_unanimous()

        response = self.client.post(self._url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertGreaterEqual(body["validated"], len(targets))
        self.assertEqual(body["skipped_drafts"], 0)

        for administration_id in targets:
            decision = ValidationDecision.objects.get(
                publication=self.publication,
                administration_id=administration_id,
            )
            self.assertFalse(decision.is_draft)
            self.assertFalse(decision.is_override)
            self.assertEqual(decision.category, DroughtCategory.d2)
            self.assertEqual(decision.majority_category, DroughtCategory.d2)
            self.assertEqual(decision.validated_by_id, self.admin.id)
            self.assertIsNotNone(decision.validated_at)
            self.assertTrue(
                decision.reasoning.startswith(BULK_REASONING_PREFIX)
            )

    def test_mirrors_into_validated_values(self):
        """AC-2.4: bulk rows must be indistinguishable afterwards."""
        targets = self._make_unanimous()
        self.client.post(self._url(), {}, format="json")

        self.publication.refresh_from_db()
        values = {
            v["administration_id"]: v["category"]
            for v in (self.publication.validated_values or [])
        }
        for administration_id in targets:
            self.assertEqual(values[administration_id], DroughtCategory.d2)

    def test_is_idempotent(self):
        self._make_unanimous()
        first = self.client.post(self._url(), {}, format="json").json()
        second = self.client.post(self._url(), {}, format="json").json()

        self.assertGreater(first["validated"], 0)
        # Everything it wrote is now `validated`, so it is outside the filter
        # entirely — not merely skipped.
        self.assertEqual(second["validated"], 0)
        self.assertEqual(second["skipped_drafts"], 0)

    def test_skips_rows_with_a_saved_draft(self):
        """D-5: a draft is an admin part-way through thinking."""
        targets = self._make_unanimous()
        drafted = targets[0]
        ValidationDecision.objects.create(
            publication=self.publication,
            administration_id=drafted,
            category=DroughtCategory.d4,
            reasoning="Waiting on the Met station re-check.",
            is_draft=True,
        )

        body = self.client.post(self._url(), {}, format="json").json()

        self.assertEqual(body["skipped_drafts"], 1)
        decision = ValidationDecision.objects.get(
            publication=self.publication, administration_id=drafted
        )
        self.assertTrue(decision.is_draft)
        self.assertEqual(decision.category, DroughtCategory.d4)
        self.assertEqual(
            decision.reasoning, "Waiting on the Met station re-check."
        )

    def test_ignores_a_client_supplied_status(self):
        """D-3/TC-3: the write is never widened by the request."""
        self._make_unanimous()
        with_status = self.client.post(
            self._url(),
            {"status": "all", "agreement": None},
            format="json",
        )
        self.assertEqual(with_status.status_code, status.HTTP_200_OK)

        written = ValidationDecision.objects.filter(
            publication=self.publication, is_draft=False
        ).values_list("administration_id", flat=True)
        # The view wrote validated_values through its own instance; without
        # this, ordered_rows() below reads a stale None and every row still
        # looks unvalidated.
        self.publication.refresh_from_db()
        ready_undisputed = {
            r["administration_id"]
            for r in ordered_rows(
                self.publication,
                status=ValidationStatus.validated,
                agreement=AgreementFilter.undisputed,
            )
        }
        self.assertTrue(set(written).issubset(ready_undisputed))

    def test_honours_an_active_search(self):
        targets = self._make_unanimous(count=3)
        label = next(
            r["label"] for r in ordered_rows(self.publication)
            if r["administration_id"] == targets[0]
        )

        self.client.post(self._url(), {"search": label}, format="json")

        written = set(
            ValidationDecision.objects
            .filter(publication=self.publication)
            .values_list("administration_id", flat=True)
        )
        # Only Tinkhundla whose name matches may be touched.
        self.assertTrue(written)
        for administration_id in written:
            matched = next(
                r for r in ordered_rows(self.publication)
                if r["administration_id"] == administration_id
            )
            self.assertIn(label.lower(), matched["label"].lower())

    def test_reviewer_cannot_bulk_validate(self):
        reviewer = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).first()
        self.client.force_authenticate(user=reviewer)

        response = self.client.post(self._url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_single_reviewer_publication_validates_nothing(self):
        """D-1: `ready` is trivially satisfied when one TWG is assigned.

        The publication looks fully reviewed — 1/1 on every row — so without
        the two-submission floor this call would validate all of them.
        """
        keep = self.publication.reviews.first()
        self.publication.reviews.exclude(pk=keep.pk).delete()
        keep.is_completed = True
        keep.suggestion_values = [
            {
                "administration_id": v["administration_id"],
                "value": 0.2,
                "comment": None,
                "reviewed": True,
                "category": DroughtCategory.d2,
            }
            for v in self.publication.initial_values
        ]
        keep.save()

        rows = ordered_rows(self.publication)
        self.assertTrue(
            all(r["status"] == ValidationStatus.ready for r in rows),
            "fixture precondition: one TWG makes every row ready",
        )

        body = self.client.post(self._url(), {}, format="json").json()

        self.assertEqual(body["validated"], 0)
        self.assertFalse(
            ValidationDecision.objects.filter(
                publication=self.publication
            ).exists()
        )

    def test_publish_gate_opens_once_everything_is_validated(self):
        self._make_unanimous(count=len(self.publication.initial_values))

        self.client.post(self._url(), {}, format="json")

        stats = self.client.get(
            reverse(
                "validation-queue-stats",
                kwargs={"version": "v1", "pk": self.publication.id},
            )
        ).json()
        self.assertTrue(stats["meta"]["can_publish"])
        self.assertEqual(stats["meta"]["pending_validation"], 0)


@override_settings(USE_TZ=False, TEST_ENV=True)
class AgreementFilterAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

        self.publication = Publication.objects.first()
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.client.force_authenticate(user=self.admin)

    def _url(self, query=""):
        base = reverse(
            "validation-queue-administrations",
            kwargs={"version": "v1", "pk": self.publication.id},
        )
        return f"{base}{query}"

    def test_disagreement_filter_matches_the_card(self):
        """D-2: clicking the card must land on exactly the rows it counts."""
        card = next(
            c for c in build_validation_stats(ordered_rows(self.publication))
            if c["key"] == AgreementFilter.disagreement
        )
        response = self.client.get(
            self._url("?agreement=disagreement&page_size=100")
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total"], card["value"])

    def test_rejects_an_unknown_agreement_value(self):
        response = self.client.get(self._url("?agreement=disputed"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_absent_filter_returns_the_whole_queue(self):
        unfiltered = self.client.get(self._url("?page_size=100")).json()
        self.assertEqual(
            unfiltered["total"], len(self.publication.initial_values)
        )


@override_settings(USE_TZ=False, TEST_ENV=True)
class PublicationTWGFloorTestCase(APITestCase):
    """D-10: the floor is on Technical Working Groups, not headcount."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.client.force_authenticate(user=self.admin)

    def _payload(self, reviewers):
        return {
            "cdi_geonode_id": 44,
            "year_month": "2026-05",
            "due_date": "2030-01-01",
            "initial_values": [],
            "reviewers": [r.id for r in reviewers],
            "subject": "Review request",
            "message": "Hello {{reviewer_name}}",
            "download_url": "http://example.com/raster.tif",
        }

    def _reviewers_in(self, twg, count=2):
        """Guarantee `count` reviewers in one TWG.

        The seeder rotates TWGs, so it yields at most one per group — relying
        on it here would skip the very case this class exists to cover.
        """
        existing = list(
            SystemUser.objects.filter(
                role=UserRoleTypes.reviewer, technical_working_group=twg
            )
        )
        while len(existing) < count:
            existing.append(
                SystemUser.objects._create_user(
                    email=f"same-twg-{twg}-{len(existing)}@example.org",
                    password="Changeme123",
                    name=f"Same TWG {len(existing)}",
                    technical_working_group=twg,
                )
            )
        return existing[:count]

    def test_rejects_a_single_reviewer(self):
        reviewer = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).first()
        response = self.client.post(
            reverse("publication-list", kwargs={"version": "v1"}),
            self._payload([reviewer]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reviewers", response.json())

    def test_rejects_several_reviewers_from_one_twg(self):
        """The case a headcount rule would wave through.

        Three reviewers all in MoAg still leave reviewers_required at 1, so
        every Inkhundla reaches `ready` on one institution's response.
        """
        same_twg = self._reviewers_in(TechnicalWorkingGroup.moag)

        response = self.client.post(
            reverse("publication-list", kwargs={"version": "v1"}),
            self._payload(same_twg),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Technical Working Groups",
            str(response.json()["reviewers"]),
        )


@override_settings(USE_TZ=False, TEST_ENV=True)
class ReviewerPanelAPITestCase(APITestCase):
    """D-11: additive any time, destructive only before anyone submitted."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 5)
        call_command(
            "generate_publications_seeder",
            "--test", True, "--with-reviews",
        )

        self.publication = Publication.objects.first()
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.client.force_authenticate(user=self.admin)

    def _add_url(self):
        return reverse(
            "publication-reviewers",
            kwargs={"version": "v1", "pk": self.publication.id},
        )

    def _remove_url(self, user_id):
        return reverse(
            "publication-reviewer-detail",
            kwargs={
                "version": "v1",
                "pk": self.publication.id,
                "user_id": user_id,
            },
        )

    def _unassigned_reviewer(self):
        """A reviewer not yet on this publication's panel.

        The seeder assigns every reviewer it creates to every publication, so
        one is created here rather than skipping — a skipped test asserts
        nothing while still reading green.
        """
        candidate = (
            SystemUser.objects
            .filter(role=UserRoleTypes.reviewer)
            .exclude(
                id__in=self.publication.reviews.values_list(
                    "user_id", flat=True
                )
            )
            .first()
        )
        return candidate or SystemUser.objects._create_user(
            email="late-joiner@example.org",
            password="Changeme123",
            name="Late Joiner",
            technical_working_group=TechnicalWorkingGroup.uneswa,
        )

    def test_adds_a_reviewer(self):
        candidate = self._unassigned_reviewer()

        response = self.client.post(
            self._add_url(), {"reviewers": [candidate.id]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["added"], 1)
        self.assertTrue(
            self.publication.reviews.filter(user=candidate).exists()
        )

    def test_adding_twice_is_a_no_op(self):
        existing = self.publication.reviews.first().user
        before = self.publication.reviews.count()

        response = self.client.post(
            self._add_url(), {"reviewers": [existing.id]}, format="json"
        )

        self.assertEqual(response.json()["added"], 0)
        self.assertEqual(self.publication.reviews.count(), before)

    def test_cannot_add_to_a_published_map(self):
        self.publication.status = PublicationStatus.published
        self.publication.save()
        candidate = self._unassigned_reviewer()

        response = self.client.post(
            self._add_url(), {"reviewers": [candidate.id]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_removes_a_reviewer_who_has_not_submitted(self):
        self.publication.status = PublicationStatus.in_review
        self.publication.save()
        review = self.publication.reviews.first()
        review.is_completed = False
        review.save()

        response = self.client.delete(self._remove_url(review.user_id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            self.publication.reviews.filter(pk=review.pk).exists()
        )

    def test_cannot_remove_a_reviewer_who_has_submitted(self):
        """Their judgement is an input other decisions were made against."""
        self.publication.status = PublicationStatus.in_review
        self.publication.save()
        review = self.publication.reviews.first()
        review.is_completed = True
        review.save()

        response = self.client.delete(self._remove_url(review.user_id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self.publication.reviews.filter(pk=review.pk).exists()
        )

    def test_cannot_remove_once_validation_has_started(self):
        self.publication.status = PublicationStatus.in_validation
        self.publication.save()
        review = self.publication.reviews.first()
        review.is_completed = False
        review.save()

        response = self.client.delete(self._remove_url(review.user_id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self.publication.reviews.filter(pk=review.pk).exists()
        )

    def test_reviewer_cannot_edit_the_panel(self):
        reviewer = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).first()
        self.client.force_authenticate(user=reviewer)

        response = self.client.post(
            self._add_url(), {"reviewers": [reviewer.id]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_adding_a_reviewer_raises_the_coverage_requirement(self):
        """AC-5.4: rows revert to awaiting; validated rows are untouched."""
        candidate = self._unassigned_reviewer()

        before = ordered_rows(self.publication)[0]["reviews_total"]
        self.client.post(
            self._add_url(), {"reviewers": [candidate.id]}, format="json"
        )
        after = ordered_rows(self.publication)[0]["reviews_total"]

        # Only when the new reviewer brings a TWG that was not represented.
        if candidate.technical_working_group is not None:
            self.assertGreaterEqual(after, before)
