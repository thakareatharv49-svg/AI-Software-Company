from pathlib import Path


class FileTools:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()

    def _safe_path(self, path: str) -> Path:
        target = (self.workspace / path).resolve()

        if target != self.workspace and self.workspace not in target.parents:
            raise PermissionError("Path is outside the workspace")

        return target

    def read_file(self, path: str) -> str:
        target = self._safe_path(path)
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        return f"File written: {target.relative_to(self.workspace)}"
