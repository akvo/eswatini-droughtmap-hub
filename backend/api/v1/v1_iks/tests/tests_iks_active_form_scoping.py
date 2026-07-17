from django.utils import timezone
from rest_framework import status
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from .base import BaseIKSTestCase


class IKSActiveFormScopingTests(BaseIKSTestCase):
    """The KoboForm `active` flag is the switch deciding which form's data is
    public. Deactivating a form must hide its data from every endpoint while
    leaving the rows in the DB for re-activation."""

    def setUp(self):
        super().setUp()
        self.indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="Indicator Frogs", section="B"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=900,
            submission_time=timezone.now(),
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=900,
            administration=self.admin_area,
            iks_indicator=self.indicator,
            value="observed",
        )

    def deactivate_form(self):
        self.form.active = False
        self.form.save()

    def test_indicators_hidden_when_form_deactivated(self):
        response = self.client.get("/api/v1/iks/indicators")
        self.assertEqual(len(response.json()), 1)

        self.deactivate_form()
        response = self.client.get("/api/v1/iks/indicators")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_bulk_series_hidden_when_form_deactivated(self):
        url = f"/api/v1/iks/{self.admin_area.id}/series?bulk=true"
        response = self.client.get(url)
        self.assertEqual(len(response.json()["indicators"]), 1)

        self.deactivate_form()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["indicators"], {})

    def test_stats_hidden_when_form_deactivated(self):
        url = f"/api/v1/iks/{self.admin_area.id}/stats"
        self.assertEqual(
            self.client.get(url).json()["total_reports_received"], 1
        )

        self.deactivate_form()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total_reports_received"], 0)

    def test_deactivating_a_form_keeps_its_rows(self):
        """Hidden from the API, but still in the DB for re-activation."""
        self.deactivate_form()
        self.assertEqual(IKSValue.objects.count(), 1)
        self.assertEqual(KoboData.objects.count(), 1)
        self.assertEqual(IKSIndicator.objects.count(), 1)
