from pathlib import Path

import pytest

from src.company.github_native import GitHubNativeService


class FakeGitHub:
    async def open_pull_request(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_github_native_writes_only_inside_workspace(tmp_path: Path):
    service = GitHubNativeService(github=FakeGitHub())
    await service.write_files(tmp_path, {"src/main.py": "print('ok')"})

    assert (tmp_path / "src/main.py").read_text(encoding="utf-8") == "print('ok')"

    with pytest.raises(ValueError):
        await service.write_files(tmp_path, {"../escape.py": "bad"})
