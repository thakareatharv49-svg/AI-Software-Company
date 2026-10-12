import asyncio
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import BinaryIO

from src.sandbox.models.contracts import (
    SandboxLimits,
    SandboxRequest,
    SandboxResult,
)
from src.sandbox.models.enums import SandboxStatus
from src.config.settings import settings


class SandboxExecutor:
    """Bounded subprocess runner with an optional OS-isolated Docker backend."""

    ALLOWED_COMMANDS = {
        "python",
        "python.exe",
        "pytest",
        "pytest.exe",
        "node",
        "node.exe",
    }

    SAFE_ENVIRONMENT_KEYS = {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
        "USERPROFILE", "HOME", "USERNAME", "USER", "LANG", "LC_ALL", "VIRTUAL_ENV",
    }

    def __init__(
        self,
        allowed_commands: set[str] | None = None,
        workspace: str | Path | None = None,
        default_limits: SandboxLimits | None = None,
        mode: str | None = None,
        container_image: str | None = None,
    ) -> None:
        self.allowed_commands = (
            allowed_commands if allowed_commands is not None else self.ALLOWED_COMMANDS
        )
        self.workspace = Path(workspace).resolve() if workspace is not None else None
        self.default_limits = default_limits or SandboxLimits()
        self.mode = (mode or settings.sandbox_mode).strip().lower()
        self.container_image = container_image or settings.sandbox_container_image
        if self.mode not in {"host", "container"}:
            raise ValueError("Sandbox mode must be 'host' or 'container'")

    def _validate(self, request: SandboxRequest) -> Path:
        if not request.command:
            raise ValueError("Sandbox command cannot be empty")
        executable = Path(request.command[0]).name.lower()
        if executable not in {command.lower() for command in self.allowed_commands}:
            raise PermissionError(
                f"Command '{request.command[0]}' is not allowed in sandbox"
            )

        working_directory = Path(request.working_directory).resolve()
        if not working_directory.exists():
            raise FileNotFoundError(f"Working directory does not exist: {working_directory}")
        if not working_directory.is_dir():
            raise NotADirectoryError(f"Working directory is not a directory: {working_directory}")
        if self.workspace is not None:
            try:
                working_directory.relative_to(self.workspace)
            except ValueError as exc:
                raise PermissionError(
                    "Working directory is outside the sandbox workspace"
                ) from exc
        return working_directory

    def _build_environment(self) -> dict[str, str]:
        environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in self.SAFE_ENVIRONMENT_KEYS
        }
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        return environment

    @staticmethod
    def _normalize_python_command(command: list[str]) -> list[str]:
        """Run Python/pytest with the interpreter hosting this application."""
        if not command:
            return command
        executable = Path(command[0]).name.lower()
        if executable in {"python", "python.exe"}:
            return [sys.executable, *command[1:]]
        if executable in {"pytest", "pytest.exe"}:
            return [sys.executable, "-m", "pytest", *command[1:]]
        return command

    @staticmethod
    def _read_bounded(stream: BinaryIO, output: bytearray, max_bytes: int) -> None:
        """Drain a pipe to avoid child-process deadlocks while retaining bounded bytes."""
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            remaining = max_bytes - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])

    @staticmethod
    def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
        """Kill the POSIX process group; fall back to terminating the direct child."""
        if process.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
                return
            except ProcessLookupError:
                return
            except OSError:
                pass
        process.kill()

    async def execute(self, request: SandboxRequest) -> SandboxResult:
        """Use a worker thread for compatibility with Windows ASGI event loops."""
        return await asyncio.to_thread(self.execute_sync, request)

    def _execute_container(self, request: SandboxRequest) -> SandboxResult:
        """Run code in a networkless container with a size-limited ephemeral workspace."""
        command = list(request.command)
        executable = Path(command[0]).name.lower() if command else ""
        aliases = {
            "python.exe": "python",
            "pytest.exe": "pytest",
            "node.exe": "node",
        }
        if command and executable in aliases:
            command[0] = aliases[executable]
        request = request.model_copy(update={"command": command})
        working_directory = self._validate(request)
        mount_root = self.workspace or working_directory
        try:
            relative_workdir = working_directory.relative_to(mount_root).as_posix()
        except ValueError as exc:
            raise PermissionError("Working directory is outside the container workspace") from exc
        container_workdir = (
            "/workspace" if relative_workdir == "." else "/workspace/" + relative_workdir
        )
        uid_gid = (
            f"{os.getuid()}:{os.getgid()}" if os.name == "posix" else "0:0"
        )
        cid_fd, cid_path = tempfile.mkstemp(prefix="asc-sandbox-", suffix=".cid")
        os.close(cid_fd)
        os.unlink(cid_path)
        cli_env = {"PATH": os.environ.get("PATH", "")}
        for key in (
            "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CERT_PATH",
            "DOCKER_TLS_VERIFY", "DOCKER_CONFIG", "HOME", "USERPROFILE",
        ):
            if key in os.environ:
                cli_env[key] = os.environ[key]
        create_command = [
            "docker", "run", "--rm", "--detach", "--pull=never", "--cidfile", cid_path,
            "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=64",
            "--memory=512m", "--cpus=1", "--ulimit", "nofile=128:128",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs", "/workspace:rw,exec,nosuid,nodev,size=512m,mode=1777",
            # Start from an existing writable tmpfs path: Docker creates the workdir
            # before mounting tmpfs, which fails when the image rootfs is read-only.\n            "--workdir", "/tmp", "--user", uid_gid,
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "PYTHONNOUSERSITE=1", "--env", "HOME=/tmp",
            "--env", "TMPDIR=/tmp", self.container_image, "sleep", "infinity",
        ]
        started = time.perf_counter()
        process: subprocess.Popen[bytes] | None = None
        stdout_bytes = bytearray()
        stderr_bytes = bytearray()
        timed_out = False
        try:
            created = subprocess.run(
                create_command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=cli_env,
            )
            if created.returncode != 0:
                return SandboxResult(
                    status=SandboxStatus.FAILED,
                    stderr=(created.stderr or created.stdout or "")[:2000],
                    error="Could not start the isolated container",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            container_id = Path(cid_path).read_text(encoding="utf-8").strip()
            source_path = str(mount_root) + os.sep + "."
            copied = subprocess.run(
                ["docker", "cp", "--archive", source_path, f"{container_id}:/tmp/"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=cli_env,
            )
            if copied.returncode != 0:
                return SandboxResult(
                    status=SandboxStatus.FAILED,
                    stderr=(copied.stderr or copied.stdout or "")[:2000],
                    error="Could not stage the project into the bounded sandbox workspace",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            staged = subprocess.run(
                ["docker", "exec", container_id, "cp", "-a", "/tmp/.", "/workspace/"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=cli_env,
            )
            if staged.returncode != 0:
                return SandboxResult(
                    status=SandboxStatus.FAILED,
                    stderr=(staged.stderr or staged.stdout or "")[:2000],
                    error="Could not copy staged project into the bounded sandbox workspace",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )

            docker_exec = [
                "docker", "exec", "--workdir", container_workdir, "--user", uid_gid,
                "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "PYTHONNOUSERSITE=1",
                "--env", "HOME=/tmp", "--env", "TMPDIR=/tmp",
                container_id, *request.command,
            ]
            popen_kwargs: dict[str, object] = {}
            if os.name == "posix":
                popen_kwargs["start_new_session"] = True
            process = subprocess.Popen(
                docker_exec,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=cli_env,
                **popen_kwargs,
            )
            assert process.stdout is not None
            assert process.stderr is not None
            stdout_thread = threading.Thread(
                target=self._read_bounded,
                args=(process.stdout, stdout_bytes, request.limits.max_output_bytes),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=self._read_bounded,
                args=(process.stderr, stderr_bytes, request.limits.max_output_bytes),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            try:
                process.wait(timeout=request.limits.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._terminate_process_tree(process)
                process.wait()
            stdout_thread.join()
            stderr_thread.join()
        except FileNotFoundError:
            return SandboxResult(
                status=SandboxStatus.FAILED,
                error="Docker is unavailable; isolated execution was refused",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                error="Timed out while preparing the isolated workspace",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        finally:
            self._stop_container(cid_path)
            try:
                Path(cid_path).unlink(missing_ok=True)
            except OSError:
                pass

        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = bytes(stdout_bytes).decode("utf-8", errors="replace")
        stderr = bytes(stderr_bytes).decode("utf-8", errors="replace")
        if timed_out:
            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr,
                error="Container command timed out and was stopped",
            )
        assert process is not None
        status = SandboxStatus.SUCCESS if process.returncode == 0 else SandboxStatus.FAILED
        return SandboxResult(
            status=status,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            error=None if process.returncode == 0 else "Container command failed",
        )

    @staticmethod
    def _stop_container(cid_path: str) -> None:
        """Stop/remove the isolated container if it still exists."""
        try:
            container_id = Path(cid_path).read_text(encoding="utf-8").strip()
        except OSError:
            return
        if not container_id or not all(
            char in "0123456789abcdef" for char in container_id.lower()
        ):
            return
        for command in (
            ["docker", "kill", container_id],
            ["docker", "rm", "-f", container_id],
        ):
            try:
                subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                    env={"PATH": os.environ.get("PATH", "")},
                )
            except (OSError, subprocess.TimeoutExpired):
                pass

    def execute_sync(self, request: SandboxRequest) -> SandboxResult:
        if self.mode == "container":
            return self._execute_container(request)
        command = self._normalize_python_command(request.command)
        request = request.model_copy(update={"command": command})
        working_directory = self._validate(request)
        started = time.perf_counter()
        popen_kwargs: dict[str, object] = {}
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            request.command,
            cwd=str(working_directory),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._build_environment(),
            **popen_kwargs,
        )
        stdout_bytes = bytearray()
        stderr_bytes = bytearray()
        assert process.stdout is not None
        assert process.stderr is not None
        stdout_thread = threading.Thread(
            target=self._read_bounded,
            args=(process.stdout, stdout_bytes, request.limits.max_output_bytes),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=self._read_bounded,
            args=(process.stderr, stderr_bytes, request.limits.max_output_bytes),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            process.wait(timeout=request.limits.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate_process_tree(process)
            process.wait()

        stdout_thread.join()
        stderr_thread.join()
        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = bytes(stdout_bytes).decode("utf-8", errors="replace")
        stderr = bytes(stderr_bytes).decode("utf-8", errors="replace")

        if timed_out:
            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr,
                error="Sandbox command timed out; process termination requested",
            )

        status = SandboxStatus.SUCCESS if process.returncode == 0 else SandboxStatus.FAILED
        return SandboxResult(
            status=status,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
