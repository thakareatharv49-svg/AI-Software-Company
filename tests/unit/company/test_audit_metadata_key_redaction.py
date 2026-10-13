from src.company.persistence import _bounded_audit_value


def test_bounded_audit_value_redacts_sensitive_metadata_keys():
    result = _bounded_audit_value({"password=secret-value": "ordinary metadata"})
    assert "secret-value" not in str(result)
    assert result != {"password=secret-value": "ordinary metadata"}


def test_bounded_audit_value_still_bounds_metadata_keys():
    key = "x" * 200
    result = _bounded_audit_value({key: "value"})
    assert list(result) == ["x" * 120]
