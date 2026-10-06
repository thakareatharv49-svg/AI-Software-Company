from __future__ import annotations

from pathlib import Path

import pytest

from src.company.workspace import ProjectExecutionService, ProjectWorkspace


def test_workspace_file_lifecycle(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(tmp_path, "demo")

    created = workspace.write_file(
        "src/main.py",
        "print('hello')",
    )

    assert created.path == "src/main.py"
    assert workspace.read_file("src/main.py") == "print('hello')"

    workspace.delete_file("src/main.py")

    assert workspace.list_files() == ()


def test_workspace_blocks_parent_escape(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(tmp_path, "demo")

    with pytest.raises(ValueError, match="escapes workspace"):
        workspace.write_file("../outside.txt", "blocked")


def test_workspace_blocks_absolute_escape(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(tmp_path, "demo")

    with pytest.raises(ValueError, match="absolute paths"):
        workspace.write_file(
            str(tmp_path / "outside.txt"),
            "blocked",
        )


@pytest.mark.asyncio
async def test_workspace_executes_python(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(tmp_path, "demo")

    result = await workspace.execute(
        (
            "python",
            "-c",
            "print('hello from workspace')",
        )
    )

    assert result.exit_code == 0
    assert "hello from workspace" in result.stdout


@pytest.mark.asyncio
async def test_workspace_captures_failure(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(tmp_path, "demo")

    result = await workspace.execute(
        (
            "python",
            "-c",
            "raise SystemExit(7)",
        )
    )

    assert result.exit_code == 7


def test_workspace_rejects_unsafe_executable(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(tmp_path, "demo")

    with pytest.raises(PermissionError, match="not allowed"):
        workspace.execute_sync(
            (
                "powershell",
                "-Command",
                "Write-Output blocked",
            )
        )


@pytest.mark.asyncio
async def test_execution_service_runs_test_build_and_artifact(
    tmp_path: Path,
) -> None:
    service = ProjectExecutionService(tmp_path)
    workspace = service.create_workspace("demo")

    workspace.write_file(
        "test_demo.py",
        "def test_demo():\n    assert 1 + 1 == 2\n",
    )
    workspace.write_file(
        "build_output.txt",
        "artifact",
    )

    result = await service.execute(
        workspace,
        test_command=(
            __import__("sys").executable,
            "-m",
            "pytest",
            "-q",
        ),
        build_command=(
            "python",
            "-c",
            "print('build ok')",
        ),
        artifact_patterns=("build_output.txt",),
    )

    assert result.test_result is not None
    assert result.test_result.exit_code == 0
    assert result.build_result is not None
    assert result.build_result.exit_code == 0
    assert [item.path for item in result.artifacts] == [
        "build_output.txt"
    ]


@pytest.mark.asyncio
async def test_failed_test_stops_build(tmp_path: Path) -> None:
    service = ProjectExecutionService(tmp_path)
    workspace = service.create_workspace("demo")

    result = await service.execute(
        workspace,
        test_command=(
            "python",
            "-c",
            "raise SystemExit(1)",
        ),
        build_command=(
            "python",
            "-c",
            "raise SystemExit(2)",
        ),
    )

    assert result.test_result is not None
    assert result.test_result.exit_code == 1
    assert result.build_result is None
    assert result.artifacts == ()


def test_artifact_size_limit(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.create(
        tmp_path,
        "demo",
        max_artifact_bytes=3,
    )

    workspace.write_file(
        "artifact.bin",
        b"1234",
    )

    with pytest.raises(
        ValueError,
        match="artifact exceeds size limit",
    ):
        workspace.collect_artifacts(("artifact.bin",))


