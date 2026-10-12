from fastapi import HTTPException

from src.company import review_routes


def test_security_gate_blocks_embedded_credentials_without_echoing_them() -> None:
    secret = "this-is-a-real-looking-secret-value"
    files = {"settings.py": f'api_key = "{secret}"'}

    try:
        review_routes._assert_artifact_security("test-mission", files)
    except HTTPException as exc:
        assert exc.status_code == 409
        assert secret not in str(exc.detail)
        assert "secret-assignment" in str(exc.detail)
    else:
        raise AssertionError("Artifact containing a credential must be blocked")


def test_security_gate_blocks_dangerous_command_patterns() -> None:
    files = {"runner.py": "import os\nos.system(command)"}

    try:
        review_routes._assert_artifact_security("test-mission", files)
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "dangerous-command" in str(exc.detail)
    else:
        raise AssertionError("Dangerous command pattern must block release")


def test_security_gate_allows_safe_source() -> None:
    review_routes._assert_artifact_security(
        "test-mission",
        {"index.html": "<main>Welcome</main>", "app.js": "const ready = true;"},
    )
