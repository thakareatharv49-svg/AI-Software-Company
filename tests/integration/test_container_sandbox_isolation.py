import os
from pathlib import Path

import pytest

from src.sandbox import SandboxExecutor, SandboxLimits, SandboxRequest, SandboxStatus


@pytest.mark.skipif(
    not os.getenv("ASC_SANDBOX_TEST_IMAGE"),
    reason="Docker isolation test image is not configured",
)
def test_container_hides_host_secrets_and_has_no_network(tmp_path: Path, monkeypatch) -> None:
    image = os.environ["ASC_SANDBOX_TEST_IMAGE"]
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_secret = tmp_path / "host-secret.txt"
    outside_secret.write_text("host-only-file-content", encoding="utf-8")
    monkeypatch.setenv("ASC_SANDBOX_HOST_SECRET", "host-only-environment-value")

    code = (
        "import os, socket\n"
        "print(\"EUID\", os.geteuid() if hasattr(os, \"geteuid\") else \"unavailable\")\n"
        "try:\n"
        f" open({str(outside_secret)!r}, encoding='utf-8').read()\n"
        " print('HOST_FILE_VISIBLE')\n"
        "except FileNotFoundError:\n"
        " print('HOST_FILE_BLOCKED')\n"
        "print(os.getenv('ASC_SANDBOX_HOST_SECRET', 'HOST_ENV_BLOCKED'))\n"
        "try:\n"
        " socket.create_connection(('1.1.1.1', 80), timeout=1)\n"
        " print('NETWORK_VISIBLE')\n"
        "except OSError:\n"
        " print('NETWORK_BLOCKED')\n"
    )
    result = SandboxExecutor(
        workspace=workspace,
        mode="container",
        container_image=image,
    ).execute_sync(
        SandboxRequest(
            command=["python", "-c", code],
            working_directory=str(workspace),
            limits=SandboxLimits(timeout_seconds=20, max_output_bytes=2000),
        )
    )

    assert result.status == SandboxStatus.SUCCESS, result.stderr
    assert "EUID 0" not in result.stdout, "generated code must never run as root"
    assert "HOST_FILE_BLOCKED" in result.stdout
    assert "HOST_ENV_BLOCKED" in result.stdout
    assert "NETWORK_BLOCKED" in result.stdout
    assert "host-only-file-content" not in result.stdout
    assert "host-only-environment-value" not in result.stdout
