from pathlib import Path
import subprocess


class GitWriteTools:
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

    def commit(self, message: str) -> str:
        message = message.strip()

        if not message:
            raise ValueError("Commit message cannot be empty")

        self._run(["add", "-A"])

        return self._run(["commit", "-m", message])

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
    ) -> str:
        args = ["push", remote]

        if branch:
            args.append(branch)

        return self._run(args)
