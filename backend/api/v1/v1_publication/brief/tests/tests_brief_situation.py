from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_users.models import SystemUser


class BriefSituationAPITestCase(APITestCase):
    """The generated "Situation this period" draft (BB-3 D-2).

    The rule under test is the one that makes a generated paragraph safe to
    forward: a clause whose source is silent is DROPPED, never softened into a
    hedge. An Inkhundla with nothing behind it must therefore yield an empty
    string and an empty `sources` list — not a sentence built on assumptions.
    """

    def setUp(self):
        self.user = SystemUser.objects.create(
            email="reviewer@example.com",
            name="Reviewer",
            role=2,
            technical_working_group=1,
        )
        self.administration = Administration.objects.create(
            name="Ngudzeni", region="Shiselweni"
        )
        self.url = reverse(
            "brief-situation",
            kwargs={
                "version": "v1",
                "administration_id": self.administration.pk,
            },
        )

    def test_unauthenticated_returns_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_administration_returns_404(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(
            reverse(
                "brief-situation",
                kwargs={"version": "v1", "administration_id": 999999},
            )
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_every_source_silent_returns_200_and_empty_value(self):
        """No publication, no Indicator, no IKS rows — the endpoint must still
        answer 200 so the section degrades to an empty editor rather than
        blanking the whole brief."""
        self.client.force_authenticate(user=self.user)
        res = self.client.get(self.url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["value"], "")
        self.assertEqual(res.data["meta"]["sources"], [])
        self.assertTrue(res.data["meta"]["generated"])
        self.assertIsNone(res.data["period"])

    def test_response_carries_the_administration_it_describes(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(self.url)

        self.assertEqual(
            res.data["administration"],
            {"id": self.administration.pk, "name": "Ngudzeni"},
        )

    def test_no_clause_is_hedged_when_its_source_is_missing(self):
        """The failure this guards against is prose that says "data suggests"
        or quotes a figure nobody computed."""
        self.client.force_authenticate(user=self.user)
        value = self.client.get(self.url).data["value"]

        for hedge in ("suggests", "approximately", "estimated", "likely"):
            self.assertNotIn(hedge, value.lower())
