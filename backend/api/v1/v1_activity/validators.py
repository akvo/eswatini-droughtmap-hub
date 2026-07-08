from django.core.exceptions import ValidationError
from api.v1.v1_activity.constants import (
    TriggerOperator,
    EXPOSURE_INDICATORS,
    VALID_DCLASS,
    VULN_PHASE_MIN,
    VULN_PHASE_MAX,
)

_OPERATORS = set(TriggerOperator.FieldStr.keys())


def _is_number(x):
    # bool is an int subclass; reject it explicitly.
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _validate_op(op):
    if op not in _OPERATORS:
        raise ValidationError(f"Invalid trigger operator: {op!r}.")


def validate_triggers(value):
    """Validate the {dclass, vuln, exp, other} trigger envelope."""
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValidationError("triggers must be an object.")

    unknown = set(value) - {"dclass", "vuln", "exp", "other"}
    if unknown:
        raise ValidationError(f"Unknown trigger keys: {sorted(unknown)}.")

    dclass = value.get("dclass")
    if dclass is not None:
        if not isinstance(dclass, dict) or set(dclass) - {"class", "months"}:
            raise ValidationError("dclass must be an object {class, months}.")
        cls = dclass.get("class")
        if cls is not None and cls not in VALID_DCLASS:
            raise ValidationError("dclass.class must be one of D0..D4 (1..5) or null.")
        months = dclass.get("months", 1)
        if not isinstance(months, int) or isinstance(months, bool) or months < 1:
            raise ValidationError("dclass.months must be an integer >= 1.")

    vuln = value.get("vuln")
    if vuln is not None:
        if not isinstance(vuln, dict) or set(vuln) - {"op", "value"}:
            raise ValidationError("vuln must be an object {op, value}.")
        _validate_op(vuln.get("op"))
        phase = vuln.get("value")
        if phase not in range(VULN_PHASE_MIN, VULN_PHASE_MAX + 1):
            raise ValidationError("vuln.value must be an IPC phase 1..4.")

    exp = value.get("exp", [])
    if not isinstance(exp, list):
        raise ValidationError("exp must be a list of conditions.")
    for cond in exp:
        if not isinstance(cond, dict) or set(cond) - {"indicator", "op", "value"}:
            raise ValidationError("Each exp condition must be {indicator, op, value}.")
        if cond.get("indicator") not in EXPOSURE_INDICATORS:
            raise ValidationError(
                f"exp.indicator must be one of {EXPOSURE_INDICATORS}."
            )
        _validate_op(cond.get("op"))
        if not _is_number(cond.get("value")):
            raise ValidationError("exp.value must be a number.")

    other = value.get("other")
    if other is not None and not isinstance(other, str):
        raise ValidationError("other must be a string or null.")
