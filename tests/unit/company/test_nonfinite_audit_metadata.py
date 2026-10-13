import math

from src.company.persistence import _bounded_audit_value


def test_bounded_audit_value_normalizes_non_finite_numbers():
    assert _bounded_audit_value(float("nan")) == "[INVALID_NUMBER]"
    assert _bounded_audit_value(float("inf")) == "[INVALID_NUMBER]"
    assert _bounded_audit_value(float("-inf")) == "[INVALID_NUMBER]"
    assert _bounded_audit_value(1.5) == 1.5
    assert math.isfinite(_bounded_audit_value(1.5))
