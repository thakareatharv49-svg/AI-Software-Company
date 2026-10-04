
from pathlib import Path

import pytest

from company.runtime.security import (
    RuntimeSecurityError,
    RuntimeSecurityGuard,
    RuntimeSecurityPolicy,
)


def test_allowed_command():
    guard = RuntimeSecurityGuard()
    assert guard.validate_command(["python", "--version"]) == [
        "python",
        "--version",
    ]


def test_disallowed_command():
    guard = RuntimeSecurityGuard()

    with pytest.raises(RuntimeSecurityError):
        guard.validate_command(["powershell", "-Command", "whoami"])


def test_empty_command():
    guard = RuntimeSecurityGuard()

    with pytest.raises(RuntimeSecurityError):
        guard.validate_command([])


def test_null_byte_is_rejected():
    guard = RuntimeSecurityGuard()

    with pytest.raises(RuntimeSecurityError):
        guard.validate_command(["python", "test\x00.py"])


def test_command_length_is_limited():
    guard = RuntimeSecurityGuard(
        RuntimeSecurityPolicy(max_command_length=10)
    )

    with pytest.raises(RuntimeSecurityError):
        guard.validate_command(["python", "123456789012345"])


def test_working_directory_is_restricted(tmp_path: Path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"

    allowed.mkdir()
    outside.mkdir()

    guard = RuntimeSecurityGuard(
        RuntimeSecurityPolicy(
            allowed_working_directory=str(allowed)
        )
    )

    assert guard.validate_working_directory(allowed) == allowed.resolve()

    with pytest.raises(RuntimeSecurityError):
        guard.validate_working_directory(outside)


def test_missing_working_directory_is_rejected(tmp_path: Path):
    guard = RuntimeSecurityGuard(
        RuntimeSecurityPolicy(
            allowed_working_directory=str(tmp_path)
        )
    )

    with pytest.raises(RuntimeSecurityError):
        guard.validate_working_directory(tmp_path / "missing")


def test_sensitive_environment_is_removed():
    guard = RuntimeSecurityGuard()

    environment = {
        "PATH": "safe",
        "GITHUB_TOKEN": "secret",
        "GH_TOKEN": "secret",
        "NORMAL": "value",
    }

    sanitized = guard.sanitize_environment(environment)

    assert sanitized == {
        "PATH": "safe",
        "NORMAL": "value",
    }


def test_sensitive_environment_is_detected():
    guard = RuntimeSecurityGuard()

    with pytest.raises(RuntimeSecurityError):
        guard.validate_environment(
            {
                "PATH": "safe",
                "GITHUB_TOKEN": "secret",
            }
        )


def test_safe_environment_is_accepted():
    guard = RuntimeSecurityGuard()

    guard.validate_environment(
        {
            "PATH": "safe",
            "APP_ENV": "production",
        }
    )


def test_shell_commands_are_disabled_by_default():
    guard = RuntimeSecurityGuard()

    parts = guard.validate_command("python --version")

    assert parts == ["python", "--version"]


def test_custom_allowed_commands():
    guard = RuntimeSecurityGuard(
        RuntimeSecurityPolicy(
            allowed_commands=("git",)
        )
    )

    assert guard.validate_command(["git", "status"]) == [
        "git",
        "status",
    ]

    with pytest.raises(RuntimeSecurityError):
        guard.validate_command(["python", "--version"])
