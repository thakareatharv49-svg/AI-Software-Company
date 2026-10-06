from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class RepositoryIndex:
    files: tuple[str, ...]
    languages: tuple[str, ...]
    symbols: tuple[str, ...]

class RepositoryIntelligence:
    """Builds a lightweight deterministic repository map from paths and source text."""
    def index(self, files: dict[str, str]) -> RepositoryIndex:
        languages = set()
        symbols = []
        for path, content in files.items():
            suffix = path.rsplit(".", 1)[-1] if "." in path else ""
            if suffix:
                languages.add(suffix)
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(("def ", "class ")):
                    symbols.append(stripped.split("(", 1)[0].split(":", 1)[0])
        return RepositoryIndex(tuple(sorted(files)), tuple(sorted(languages)), tuple(symbols))
