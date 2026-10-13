from src.company.project_factory import ProjectFactory


def test_safe_error_detail_redacts_secrets_and_bounds_text():
    secret = "ghp_" + "T" * 32
    detail = ProjectFactory._safe_error_detail(
        f"RuntimeError: password=super-secret token={secret} " + ("x" * 5000)
    )

    assert "super-secret" not in detail
    assert secret not in detail
    assert "[REDACTED_TOKEN]" in detail
    assert len(detail) <= 4000
