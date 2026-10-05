from company.governance import DataClass, DataGovernance


def test_governance_detects_secret_and_pii() -> None:
    report = DataGovernance().inspect(
        "email=atharv@example.com api_key=super-secret-value"
    )
    assert report.has_secret
    assert report.has_pii


def test_secret_retention_must_be_zero() -> None:
    governance = DataGovernance()
    assert governance.retention_allowed(DataClass.SECRET, 0)
    assert not governance.retention_allowed(DataClass.SECRET, 1)
