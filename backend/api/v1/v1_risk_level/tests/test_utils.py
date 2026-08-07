from django.test import TestCase, override_settings
from django.utils import timezone

from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_publication.models import Publication, PublicationStatus
from api.v1.v1_risk_level.utils import band_thresholds, drought_trend

ADM = 1621199


@override_settings(USE_TZ=False, TEST_ENV=True)
class DroughtTrendTestCase(TestCase):
    def _publish(self, year_month, category, geonode_id):
        """One published cycle carrying this Inkhundla's class."""
        return Publication.objects.create(
            year_month=year_month,
            cdi_geonode_id=geonode_id,
            due_date="2024-12-01",
            initial_values=[],
            validated_values=(
                []
                if category is None
                else [{"administration_id": ADM, "category": category}]
            ),
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

    def _cycles(self, *categories):
        """Oldest first, so categories[-1] ends up the latest cycle."""
        for index, category in enumerate(categories, 1):
            self._publish(f"2024-{index:02d}-01", category, index)

    def test_single_cycle_has_no_trend(self):
        self._cycles(DroughtCategory.d2)
        self.assertEqual(
            drought_trend(ADM), {"trend": None, "trend_desc": None}
        )

    def test_worsening(self):
        self._cycles(DroughtCategory.d1, DroughtCategory.d3)
        self.assertEqual(
            drought_trend(ADM),
            {"trend": "worsening", "trend_desc": "1 month worsening"},
        )

    def test_recovering(self):
        self._cycles(DroughtCategory.d3, DroughtCategory.d1)
        self.assertEqual(
            drought_trend(ADM),
            {"trend": "recovering", "trend_desc": "1 month recovering"},
        )

    def test_stable_reads_as_unchanged(self):
        self._cycles(DroughtCategory.d2, DroughtCategory.d2)
        self.assertEqual(
            drought_trend(ADM),
            {"trend": "stable", "trend_desc": "1 month unchanged"},
        )

    def test_run_length_counts_consecutive_steps_only(self):
        # d0 -> d1 -> d2 -> d3 is three consecutive worsening steps...
        self._cycles(
            DroughtCategory.d0,
            DroughtCategory.d1,
            DroughtCategory.d2,
            DroughtCategory.d3,
        )
        self.assertEqual(drought_trend(ADM)["trend_desc"], "3 months worsening")

    def test_run_stops_at_direction_change(self):
        # ...but a recovery in the middle ends the run.
        self._cycles(
            DroughtCategory.d3,
            DroughtCategory.d1,
            DroughtCategory.d2,
            DroughtCategory.d3,
        )
        self.assertEqual(drought_trend(ADM)["trend_desc"], "2 months worsening")

    def test_gap_in_history_stops_the_scan(self):
        # The middle cycle has no class for this Inkhundla: comparing across
        # it would report a step that never happened.
        self._cycles(DroughtCategory.d0, None, DroughtCategory.d3)
        self.assertEqual(
            drought_trend(ADM), {"trend": None, "trend_desc": None}
        )

    def test_no_data_category_is_not_treated_as_a_class(self):
        self._cycles(DroughtCategory.d2, DroughtCategory.none)
        self.assertEqual(
            drought_trend(ADM), {"trend": None, "trend_desc": None}
        )

    def test_unpublished_cycles_are_ignored(self):
        self._cycles(DroughtCategory.d1, DroughtCategory.d3)
        Publication.objects.create(
            year_month="2024-05-01",
            cdi_geonode_id=99,
            due_date="2024-12-01",
            initial_values=[],
            validated_values=[
                {"administration_id": ADM, "category": DroughtCategory.d0}
            ],
            status=PublicationStatus.in_review,
        )
        self.assertEqual(drought_trend(ADM)["trend"], "worsening")


class BandThresholdsTestCase(TestCase):
    def test_floors_come_from_risk_bands(self):
        # watch spans High (0.30) and Moderate (0.15) -> its floor is 0.15.
        self.assertEqual(
            band_thresholds(),
            {"urgent": 0.5, "watch": 0.15, "monitor": 0.0},
        )
