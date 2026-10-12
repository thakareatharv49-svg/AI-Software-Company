from __future__ import annotations

from src.company.artifact_validation import validate_generated_artifacts
from src.company.secret_scanning import scan_generated_secrets


def test_provider_token_patterns_are_detected_without_echoing_values() -> None:
    files = {
        "app.js": "token = 'ghp_" + "A" * 32 + "'",
        "config.py": "API_KEY = 'sk-proj-" + "B" * 32 + "'",
    }
    findings = scan_generated_secrets(files)
    assert len(findings) == 2
    assert "A" * 20 not in " ".join(findings)
    assert "B" * 20 not in " ".join(findings)


def test_generic_secret_assignment_is_detected() -> None:
    findings = scan_generated_secrets({"settings.py": "password = 'this-is-not-a-real-password'"})
    assert len(findings) == 1
    assert "credential-assignment" in findings[0]
    assert "this-is-not" not in findings[0]


def test_example_placeholders_are_ignored() -> None:
    assert scan_generated_secrets({".env.example": "API_KEY=your_api_key_goes_here"}) == []


def test_artifact_validation_blocks_secret_bearing_release_files() -> None:
    issues = validate_generated_artifacts({
        "index.html": "<title>App</title>",
        "config.js": "password = 'super-secret-value-123456'",
    })
    assert any("may contain a secret" in issue for issue in issues)


def test_private_key_marker_is_reported_without_echoing_payload() -> None:
    findings = scan_generated_secrets({"key.txt": ("-" * 5) + "BEGIN PRIVATE KEY" + ("-" * 5)})
    assert len(findings) == 1
    assert "private-key" in findings[0]
    assert "PRIVATE KEY" not in findings[0]


def test_common_cloud_and_payment_credentials_are_detected_without_values() -> None:
    files = {
        "google.env": "GOOGLE_API_KEY=AIza" + "A" * 35,
        "stripe.env": "STRIPE_SECRET_KEY=sk_live_" + "B" * 24,
    }
    findings = scan_generated_secrets(files)
    assert len(findings) == 2
    assert "google-api-key" in findings[0]
    assert "stripe-secret-key" in findings[1]
    assert "A" * 20 not in " ".join(findings)
    assert "B" * 20 not in " ".join(findings)


def test_bearer_tokens_and_jwt_are_detected_without_echoing_values() -> None:
    bearer = "Bearer " + "C" * 32
    jwt = ".".join(("eyJ" + "a" * 12, "eyJ" + "b" * 12, "c" * 12))
    findings = scan_generated_secrets({
        "headers.txt": "Authorization: " + bearer,
        "session.txt": "SESSION_TOKEN=" + jwt,
    })
    assert len(findings) == 2
    assert "bearer-token" in findings[0]
    assert "jwt" in findings[1]
    assert "C" * 20 not in " ".join(findings)
    assert jwt not in " ".join(findings)


def test_database_connection_string_assignment_is_flagged() -> None:
    secret_url = "postgresql://service:password123@db.example.test/app"
    findings = scan_generated_secrets({"settings.py": "DATABASE_URL='" + secret_url + "'"})
    assert len(findings) == 1
    assert "credential-assignment" in findings[0]
    assert "password123" not in findings[0]
