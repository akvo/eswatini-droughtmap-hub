from django.test import SimpleTestCase

from api.v1.v1_activity.trigger_evaluation import activity_passes
from api.v1.v1_publication.constants import DroughtCategory


# A fully-populated administration row (all indicators present).
def _row(**over):
    row = {
        "category": DroughtCategory.d3,  # 4
        "population": 5000,
        "cropland": 2000,
        "cattle": 1600,
        "water": 1000,
        "water_demand": 1000,
        "ipc_phase": 3,
        "months_active": None,
    }
    row.update(over)
    return row


class ActivityPassesTestCase(SimpleTestCase):
    def test_empty_or_null_triggers_never_fire(self):
        self.assertFalse(activity_passes(None, _row()))
        self.assertFalse(activity_passes({}, _row()))

    def test_dclass_gate_min_category(self):
        trig = {"dclass": {"class": DroughtCategory.d3, "months": 4}}
        self.assertTrue(activity_passes(
            trig, _row(category=DroughtCategory.d3)))
        self.assertTrue(activity_passes(
            trig, _row(category=DroughtCategory.d4)))
        self.assertFalse(
            activity_passes(trig, _row(category=DroughtCategory.d2)))

    def test_dclass_none_category_excluded(self):
        trig = {"dclass": {"class": DroughtCategory.d0, "months": 1}}
        self.assertFalse(
            activity_passes(trig, _row(category=DroughtCategory.none)))
        self.assertFalse(activity_passes(trig, _row(category=None)))

    def test_null_dclass_class_is_no_gate(self):
        trig = {"dclass": {"class": None, "months": 1}}
        self.assertTrue(activity_passes(trig, _row(category=None)))

    def test_months_is_satisfied_by_omission(self):
        # months has no per-admin source -> never blocks firing.
        trig = {"dclass": {"class": DroughtCategory.d3, "months": 99}}
        self.assertTrue(activity_passes(
            trig, _row(category=DroughtCategory.d3)))

    def test_vuln_ipc_phase_evaluated(self):
        trig = {"vuln": {"op": 1, "value": 3}}  # op=1 (>=)
        self.assertTrue(activity_passes(trig, _row(ipc_phase=3)))
        self.assertTrue(activity_passes(trig, _row(ipc_phase=4)))
        self.assertFalse(activity_passes(trig, _row(ipc_phase=2)))

    def test_exp_population_evaluated(self):
        trig = {"exp": [{"indicator": "population", "op": 1, "value": 2000}]}
        self.assertTrue(activity_passes(trig, _row(population=5000)))
        self.assertFalse(activity_passes(trig, _row(population=1000)))

    def test_exp_lte_operator(self):
        trig = {"exp": [{"indicator": "population", "op": 2, "value": 2000}]}
        self.assertTrue(activity_passes(trig, _row(population=1500)))
        self.assertFalse(activity_passes(trig, _row(population=5000)))

    def test_exp_missing_real_value_fails(self):
        # population IS a real dimension; None actual -> not satisfied.
        trig = {"exp": [{"indicator": "population", "op": 1, "value": 1}]}
        self.assertFalse(activity_passes(trig, _row(population=None)))

    def test_exp_water_evaluated(self):
        trig = {"exp": [{"indicator": "water", "op": 1, "value": 500}]}
        self.assertTrue(activity_passes(trig, _row(water=1000)))
        self.assertFalse(activity_passes(trig, _row(water=200)))

    def test_multiple_exp_all_must_pass(self):
        trig = {"exp": [
            {"indicator": "cattle", "op": 1, "value": 1500},
            {"indicator": "cropland", "op": 1, "value": 3000}]}
        self.assertFalse(activity_passes(
            trig, _row(cattle=1600, cropland=2000)))
        self.assertTrue(activity_passes(
            trig, _row(cattle=1600, cropland=3200)))

    def test_unknown_indicator_fails_safe(self):
        trig = {"exp": [{"indicator": "gremlins", "op": 1, "value": 1}]}
        self.assertFalse(activity_passes(trig, _row()))

    def test_all_dimensions_anded(self):
        trig = {
            "dclass": {"class": DroughtCategory.d3, "months": 2},
            "vuln": {"op": 1, "value": 2},
            "exp": [{"indicator": "population", "op": 1, "value": 2000}]}
        self.assertTrue(activity_passes(
            trig, _row(category=DroughtCategory.d3, population=5000, ipc_phase=3)))
        self.assertFalse(activity_passes(
            trig, _row(category=DroughtCategory.d2, population=5000, ipc_phase=3)))
