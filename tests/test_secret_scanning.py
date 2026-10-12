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
    findings = scan_generated_secrets({"key.txt": "-----BEGIN PRIVATE KEY-----"})
    assert len(findings) == 1
    assert "private-key" in findings[0]
    assert "PRIVATE KEY-----" not in findings[0]
