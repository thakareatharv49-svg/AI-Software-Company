from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    required: bool
    detail: str


@dataclass(slots=True, frozen=True)
class ReadinessReport:
    ready: bool
    checks: list[ReadinessCheck]

    @property
    def failed_required(self) -> list[ReadinessCheck]:
        return [
            check
            for check in self.checks
            if check.required and not check.passed
        ]

    @property
    def failed_optional(self) -> list[ReadinessCheck]:
        return [
            check
            for check in self.checks
            if not check.required and not check.passed
        ]

    def as_dict(self) -> dict:
        return {
            "ready": self.ready,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "required": check.required,
                    "detail": check.detail,
                }
                for check in self.checks
            ],
        }


class ProductionReadiness:
    def __init__(
        self,
        *,
        project_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root or ".").resolve()

    def check_python_version(self) -> ReadinessCheck:
        version = sys.version_info
        passed = version >= (3, 11)

        return ReadinessCheck(
            name="python_version",
            passed=passed,
            required=True,
            detail=(
                f"Python {version.major}.{version.minor}.{version.micro}"
                if passed
                else "Python 3.11 or newer is required"
            ),
        )

    def check_source_tree(self) -> ReadinessCheck:
        required_paths = [
            self.project_root / "src",
            self.project_root / "tests",
        ]

        missing = [
            str(path.relative_to(self.project_root))
            for path in required_paths
            if not path.exists()
        ]

        return ReadinessCheck(
            name="source_tree",
            passed=not missing,
            required=True,
            detail=(
                "Required source and test directories are present"
                if not missing
                else f"Missing: {', '.join(missing)}"
            ),
        )

    def check_git_repository(self) -> ReadinessCheck:
        git_path = self.project_root / ".git"

        return ReadinessCheck(
            name="git_repository",
            passed=git_path.exists(),
            required=True,
            detail=(
                "Git repository detected"
                if git_path.exists()
                else "Git repository not found"
            ),
        )

    def check_required_environment(
        self,
        required_variables: list[str] | None = None,
    ) -> ReadinessCheck:
        variables = required_variables or []

        missing = [
            variable
            for variable in variables
            if not os.getenv(variable)
        ]

        return ReadinessCheck(
            name="required_environment",
            passed=not missing,
            required=True,
            detail=(
                "All required environment variables are present"
                if not missing
                else f"Missing: {', '.join(missing)}"
            ),
        )

    def check_directory_writable(
        self,
        directory: str | Path | None = None,
    ) -> ReadinessCheck:
        target = Path(directory or self.project_root)

        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".production_readiness_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()

            return ReadinessCheck(
                name="filesystem_writable",
                passed=True,
                required=True,
                detail=f"Writable: {target}",
            )
        except OSError as exc:
            return ReadinessCheck(
                name="filesystem_writable",
                passed=False,
                required=True,
                detail=str(exc),
            )

    def check_python_imports(
        self,
        modules: list[str] | None = None,
    ) -> ReadinessCheck:
        module_names = modules or ["src.company"]
        failures: list[str] = []

        for module_name in module_names:
            try:
                importlib.import_module(module_name)
            except Exception as exc:
                failures.append(
                    f"{module_name}: {type(exc).__name__}: {exc}"
                )

        return ReadinessCheck(
            name="python_imports",
            passed=not failures,
            required=True,
            detail=(
                "Core Python imports succeeded"
                if not failures
                else "; ".join(failures)
            ),
        )

    def custom_check(
        self,
        name: str,
        check: Callable[[], bool],
        *,
        required: bool = True,
        detail: str = "",
    ) -> ReadinessCheck:
        try:
            passed = bool(check())
            resolved_detail = detail or (
                "Check passed" if passed else "Check failed"
            )
        except Exception as exc:
            passed = False
            resolved_detail = f"{type(exc).__name__}: {exc}"

        return ReadinessCheck(
            name=name,
            passed=passed,
            required=required,
            detail=resolved_detail,
        )

    def run(
        self,
        *,
        required_environment: list[str] | None = None,
    ) -> ReadinessReport:
        checks = [
            self.check_python_version(),
            self.check_source_tree(),
            self.check_git_repository(),
            self.check_required_environment(required_environment),
            self.check_directory_writable(),
            self.check_python_imports(),
        ]

        ready = all(
            check.passed
            for check in checks
            if check.required
        )

        return ReadinessReport(
            ready=ready,
            checks=checks,
        )
