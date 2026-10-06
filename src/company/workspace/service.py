from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .manager import ProjectWorkspace
from .models import Artifact, CommandResult


@dataclass(frozen=True, slots=True)
class ProjectExecutionResult:
    workspace: Path
    test_result: CommandResult | None
    build_result: CommandResult | None
    artifacts: tuple[Artifact, ...]


class ProjectExecutionService:
    """Coordinates project tests, builds and artifact collection."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def create_workspace(
        self,
        project_id: str,
        **limits: object,
    ) -> ProjectWorkspace:
        return ProjectWorkspace.create(
            self.workspace_root,
            project_id,
            **limits,
        )

    async def execute(
        self,
        workspace: ProjectWorkspace,
        *,
        test_command: list[str] | tuple[str, ...] | None = None,
        build_command: list[str] | tuple[str, ...] | None = None,
        artifact_patterns: tuple[str, ...] = (
            "dist/**",
            "build/**",
            "*.whl",
        ),
    ) -> ProjectExecutionResult:
        test_result = None
        build_result = None

        if test_command is not None:
            test_result = await workspace.test(test_command)

            if (
                test_result.exit_code != 0
                or test_result.timed_out
            ):
                return ProjectExecutionResult(
                    workspace=workspace.root,
                    test_result=test_result,
                    build_result=None,
                    artifacts=(),
                )

        if build_command is not None:
            build_result = await workspace.build(build_command)

            if (
                build_result.exit_code != 0
                or build_result.timed_out
            ):
                return ProjectExecutionResult(
                    workspace=workspace.root,
                    test_result=test_result,
                    build_result=build_result,
                    artifacts=(),
                )

        artifacts = workspace.collect_artifacts(
            artifact_patterns
        )

        return ProjectExecutionResult(
            workspace=workspace.root,
            test_result=test_result,
            build_result=build_result,
            artifacts=artifacts,
        )
