"""Adversarial regression tests for generated-artifact security scanning."""
from src.security.models.contracts import SecurityScanRequest
from src.security.models.enums import SecuritySeverity, SecurityStatus
from src.security.scanning.scanner import SecurityScanner


def _scan(files: dict[str, str]):
    return SecurityScanner().scan(SecurityScanRequest(project_id="test", files=files))


def test_detects_common_provider_tokens_and_redacts_values() -> None:
    result = _scan({
        "app.py": 'GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"\n'
        'AWS_ACCESS_KEY_ID = "AKIA1234567890ABCDEF"\n'
        'DATABASE_URL = "postgresql://admin:real-password@db.example/test"'
    })

    assert result.status == SecurityStatus.FAILED
    assert len(result.findings) >= 3
    assert all(item.severity == SecuritySeverity.CRITICAL for item in result.findings)
    assert all("ghp_" not in item.message for item in result.findings)
    assert all("real-password" not in item.message for item in result.findings)


def test_detects_private_keys_bearer_tokens_and_secret_assignments() -> None:
    result = _scan({
        "config.py": 'client_secret = "a-very-real-secret-value"\n'
        'header = "Bearer abcdefghijklmnopqrstuvwxyz123456"\n'
        "key = '-----BEGIN OPENSSH PRIVATE KEY-----'"
    })

    assert result.status == SecurityStatus.FAILED
    assert {item.rule for item in result.findings} >= {
        "secret-assignment", "bearer-token", "private-key"
    }


def test_placeholder_credentials_do_not_trigger_secret_assignment_rule() -> None:
    result = _scan({"example.env": 'API_KEY="your-api-key-here"'})

    assert not any(item.rule == "secret-assignment" for item in result.findings)


def test_detects_shell_execution_and_subprocess_shell_true() -> None:
    result = _scan({
        "run.py": "os.system(command)\nsubprocess.run(command, shell=True)"
    })

    assert result.status == SecurityStatus.FAILED
    assert sum(item.rule == "dangerous-command" for item in result.findings) == 2


def test_normalizes_reported_paths_and_never_includes_source_values() -> None:
    result = _scan({"nested\\config.py": 'password = "do-not-print-this-secret"'})

    assert result.findings[0].path == "nested/config.py"
    assert "do-not-print-this-secret" not in result.findings[0].message
