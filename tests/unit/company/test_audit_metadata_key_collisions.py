from src.company.persistence import _bounded_audit_value


def test_bounded_audit_value_preserves_keys_that_collide_after_redaction():
    result = _bounded_audit_value({
        "password=first-secret-value": "first",
        "password=second-secret-value": "second",
    })
    assert len(result) == 2
    assert sorted(result.values()) == ["first", "second"]
    assert all("secret-value" not in key for key in result)


def test_bounded_audit_value_preserves_keys_that_collide_after_truncation():
    prefix = "k" * 120
    result = _bounded_audit_value({prefix + "first": 1, prefix + "second": 2})
    assert len(result) == 2
    assert sorted(result.values()) == [1, 2]
