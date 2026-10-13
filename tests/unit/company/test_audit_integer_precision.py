from src.company.persistence import _bounded_audit_value


def test_bounded_audit_value_preserves_large_integer_precision():
    safe_integer = (1 << 53) - 1
    assert _bounded_audit_value(safe_integer) == safe_integer
    assert _bounded_audit_value(-safe_integer) == -safe_integer
    assert _bounded_audit_value(safe_integer + 1) == str(safe_integer + 1)
    assert _bounded_audit_value(-(safe_integer + 1)) == str(-(safe_integer + 1))
    assert _bounded_audit_value(True) is True
