import asyncio
from pathlib import Path

import pytest

from src.company.browser_acceptance import run_browser_acceptance


def test_browser_acceptance_opens_route_and_exercises_interaction(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        """<!doctype html>
<html><head><title>Browser acceptance fixture</title></head>
<body>
  <h1>Workspace</h1>
  <button id="increment" onclick="document.querySelector('#count').textContent = Number(document.querySelector('#count').textContent) + 1">Increment</button>
  <output id="count">0</output>
  <a href="/details.html">Details</a>
</body></html>""",
        encoding="utf-8",
    )
    (tmp_path / "details.html").write_text(
        "<!doctype html><html><body><h1>Details route</h1></body></html>",
        encoding="utf-8",
    )

    result = asyncio.run(run_browser_acceptance(tmp_path))

    if result["status"] == "unavailable":
        pytest.skip(result["detail"])
    assert result["status"] == "passed", result["detail"]
    assert "/" in result["routes_checked"]
    assert "/details.html" in result["routes_checked"]
    assert result["interactions_checked"] == ["Increment"]
    assert result["page_errors"] == []
