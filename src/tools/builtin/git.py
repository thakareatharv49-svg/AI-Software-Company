from pathlib import Path
import subprocess


class GitTools:
    def __init__(
        self,
        workspace: str | Path,
        timeout_seconds: int = 30,
        max_output_chars: int = 20_000,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    def _run(self, args: list[str]) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        output = result.stdout

        if result.stderr:
            output += f"\n{result.stderr}"

        output = output[: self.max_output_chars]

        if result.returncode != 0:
            raise RuntimeError(
                f"Git command failed with exit code {result.returncode}\n{output}"
            )

        return output

    def status(self) -> str:
        return self._run(["status", "--short"])

    def diff(self) -> str:
        return self._run(["diff"])
