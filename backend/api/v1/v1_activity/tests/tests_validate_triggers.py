from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from api.v1.v1_activity.validators import validate_triggers


class ValidateTriggersTestCase(SimpleTestCase):
    def test_none_is_allowed(self):
        validate_triggers(None)  # no raise

    def test_full_valid_trigger(self):
        validate_triggers({
            "dclass": {"class": 3, "months": 4},
            "vuln": {"op": 1, "value": 2},
            "exp": [{"indicator": "population", "op": 1, "value": 2000}],
            "other": None,
        })

    def test_unknown_top_level_key_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"nope": 1})

    def test_dclass_zero_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"dclass": {"class": 0, "months": 1}})

    def test_dclass_months_must_be_positive_int(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"dclass": {"class": 3, "months": 0}})

    def test_vuln_phase_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"vuln": {"op": 1, "value": 6}})

    def test_exp_unknown_indicator_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers(
                {"exp": [{"indicator": "gdp", "op": 1, "value": 1}]}
            )

    def test_exp_must_be_list(self):
        with self.assertRaises(ValidationError):
            validate_triggers({
                "exp": {"indicator": "population", "op": 1, "value": 1}
            })

    def test_other_must_be_string_or_null(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"other": 5})

    def test_dclass_class_bool_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"dclass": {"class": True, "months": 1}})

    def test_dclass_class_float_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"dclass": {"class": 3.0, "months": 1}})

    def test_vuln_op_bool_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"vuln": {"op": True, "value": 2}})

    def test_vuln_value_bool_rejected(self):
        with self.assertRaises(ValidationError):
            validate_triggers({"vuln": {"op": 1, "value": True}})
