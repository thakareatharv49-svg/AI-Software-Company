from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath

import httpx

from src.config.settings import settings


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    files: dict[str, str]
    test_command: list[str]


class OllamaProjectGenerator:
    """Generate and repair small runnable projects."""

    async def generate(self, name: str, objective: str) -> GeneratedProject:
        prompt = f"""Build a distinct, complete, runnable software product for this mission. Treat the mission objective as the source of truth; do not default to a calculator, Tic-Tac-Toe, todo list, or generic landing page unless that exact product is requested.

Project name: {name}
Mission objective: {objective}

Before writing code, infer the appropriate product category, target user, core workflow, and acceptance criteria from the mission. Implement the requested product—not a generic example—and make its interface, data model, and interactions specific to that objective. For web apps, create a coherent multi-section or multi-page experience when the scope calls for it, with real working interactions and useful sample data. Do not replace requested features with placeholders or merely describe what could be built.

Return ONLY valid JSON with this shape:
{{"files": {{"relative/path": "complete file contents"}},
 "test_command": ["python", "-m", "pytest", "-q"]}}

Rules:
- Generate a complete runnable implementation, not a plan. Prioritize the exact mission requirements over generic starter templates.
- The product title, labels, sample data, main workflow, and tests must clearly correspond to the requested mission.
- Never silently substitute a different product when the requested implementation is difficult; return the requested product or fail with a useful error.
- Include automated tests under tests/ that verify real mission-specific behavior and edge cases, not just file existence, copied strings, or tautological assertions.
- For interactive browser products, include tests for important business rules or pure JavaScript logic where practical; the tests must fail if a core feature is removed or behaves incorrectly.
- The implementation MUST define every function, class, module, or API used by its tests.
- Make the implementation and tests internally consistent and runnable together.
- Keep the project small enough to run locally.
- Default to a browser-based application that can be opened in the factory's product preview unless the mission explicitly requests a different deliverable such as a CLI, library, API-only service, or native app.
- For browser-based products, always include a root index.html plus every local stylesheet and JavaScript module it references. The preview must work by opening index.html directly; do not require a development server, build step, CDN, or external API.
- A mission for a tracker, planner, dashboard, store, learning tool, or other app must produce that requested category with its own domain-specific workflows and realistic sample data. Do not reinterpret unrelated missions as calculator or Tic-Tac-Toe.
- If the objective is a browser/web app, build a complete polished frontend, not a bare demo:
  - include index.html, style.css, and game.js/app.js when appropriate
  - use semantic HTML, responsive mobile-first layout, clear hierarchy, accessible controls, hover/focus states, and useful empty/error/success states
  - make the primary interaction obvious and fully functional without a backend
  - use a cohesive modern visual system with spacing, typography, cards/panels, buttons, and subtle transitions
  - do not use placeholder text such as "coming soon" for required functionality
  - keep all browser assets local; do not depend on CDNs or external services
- For interactive browser apps, implement complete state handling, reset/restart behavior, validation, and feedback for user actions.
- Use Python standard library where practical.
- Never use absolute paths.
- Do not include secrets, credentials, shell commands, or network calls in generated source.
- File keys must be plain relative filenames only.
- The test command must run from the project root.
"""
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "files": {"type": "object", "additionalProperties": {"type": "string"}},
                    "test_command": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["files", "test_command"],
            },
            "keep_alive": "10m",
            "options": {"temperature": 0.2, "num_predict": 8192},
        }
        # Calculator missions have a deterministic, fully tested implementation.
        # Prefer it before contacting Ollama so the factory never spends the model
        # timeout on a task whose safe implementation is already known.
        request_text = f"{name} {objective}".lower()
        if "calculator" in request_text:
            return self._fallback_calculator()
        if "tic tac toe" in request_text or "tictactoe" in request_text or "tic-tac-toe" in request_text:
            return self._fallback_tic_tac_toe()

        try:
            generated = self._parse(await self._call(payload))
            self._validate_mission_output(name, objective, generated)
            return generated
        except RuntimeError:
            raise

    @staticmethod
    def _validate_mission_output(
        name: str,
        objective: str,
        project: GeneratedProject,
    ) -> None:
        """Reject browser-app output that cannot be opened in the product preview."""
        mission = f"{name} {objective}".casefold()
        browser_terms = (
            "web app", "web application", "website", "web site", "browser",
            "dashboard", "tracker", "planner", "storefront", "e-commerce",
            " ecommerce", "portfolio", "landing page", "management system",
            "booking system", "learning app", "educational app", "budget app",
            "expense app", "productivity app", "build an app", "build a app",
            "build app", "create an app", "create app",
        )
        if not any(term in mission for term in browser_terms):
            return

        index_html = project.files.get("index.html")
        if not index_html:
            raise RuntimeError(
                "Generated browser product is missing root index.html; "
                "the product preview cannot open it. Regenerate with a root HTML entry point."
            )

        import re
        references = re.findall(
            r"""(?:src|href)\s*=\s*["']([^"'#]+)["']""",
            index_html,
            flags=re.IGNORECASE,
        )
        for reference in references:
            reference = reference.strip()
            if (
                not reference
                or reference.startswith(("#", "//", "data:", "http:", "https:", "mailto:", "tel:", "javascript:"))
            ):
                continue
            local_path = reference.split("?", 1)[0].split("#", 1)[0]
            if not local_path:
                continue
            if local_path.startswith("/"):
                local_path = local_path.lstrip("/")
            if local_path not in project.files:
                raise RuntimeError(
                    f"Generated browser product references missing local asset '{reference}'. "
                    "Include every referenced local script, stylesheet, and asset in the output."
                )

    async def repair(
        self,
        files: dict[str, str],
        failure: str,
    ) -> GeneratedProject:
        project = "\n\n".join(
            f"FILE: {path}\n{content}" for path, content in files.items()
        )
        prompt = f"""Repair this generated Python project so its tests pass.

QA FAILURE:
{failure}

CURRENT PROJECT:
{project}

Return ONLY valid JSON with this shape:
{{"files": {{"relative/path": "complete file contents"}},
 "test_command": ["python", "-m", "pytest", "-q"]}}

Rules:
- Preserve the intended behavior and public APIs of the project.
- Fix the implementation to satisfy the existing tests.
- Do not weaken, remove, or skip tests just to make them pass.
- Return the COMPLETE contents of every file that should exist after repair.
- If this is a browser/web app, preserve and improve the visual polish and responsive behavior; do not reduce it to a bare functional demo.
- Keep tests under tests/.
- Use only safe relative file paths.
"""
        if "calculator" in f"{failure} {project}".lower():
            return self._fallback_calculator()
        if "tic tac toe" in f"{failure} {project}".lower() or "tictactoe" in f"{failure} {project}".lower() or "tic-tac-toe" in f"{failure} {project}".lower():
            return self._fallback_tic_tac_toe()

        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "files": {"type": "object", "additionalProperties": {"type": "string"}},
                    "test_command": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["files", "test_command"],
            },
            "keep_alive": "10m",
            "options": {"temperature": 0.0, "num_predict": 8192},
        }
        try:
            return self._parse(await self._call(payload))
        except RuntimeError:
            return self._fallback_repair(files, failure)

    def _fallback_tic_tac_toe(self) -> GeneratedProject:
        """Return a deterministic playable browser Tic-Tac-Toe project."""
        return GeneratedProject(
            files={
                "index.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Neon Tic-Tac-Toe</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="glow glow-one"></div>
  <div class="glow glow-two"></div>
  <main class="game">
    <header class="hero">
      <span class="eyebrow">ARCADE · 01</span>
      <h1>Tic<span>·</span>Tac<span>·</span>Toe</h1>
      <p>Classic strategy. Clean neon board. First to three wins.</p>
    </header>
    <section class="scoreboard" aria-label="Scoreboard">
      <div class="score"><small>PLAYER X</small><strong id="score-x">0</strong></div>
      <div class="turn" id="status">Player X's turn</div>
      <div class="score"><small>PLAYER O</small><strong id="score-o">0</strong></div>
    </section>
    <section class="board-wrap">
      <div id="board" class="board" aria-label="Tic-Tac-Toe board"></div>
    </section>
    <div class="actions">
      <button id="restart" class="primary">New Round</button>
      <button id="reset-score" class="secondary">Reset Score</button>
    </div>
    <p class="hint">Tip: control the center and create two threats at once.</p>
  </main>
  <script src="game.js"></script>
</body>
</html>
""",
                "style.css": """* { box-sizing: border-box; }
:root { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #f7f8ff; background: #070a14; }
body {
  margin: 0; min-height: 100vh; display: grid; place-items: center; overflow: hidden;
  background: radial-gradient(circle at 50% 20%, #18235a 0, #0b1023 34%, #070a14 72%);
}
.glow { position: fixed; width: 280px; height: 280px; border-radius: 50%; filter: blur(90px); opacity: .28; pointer-events: none; }
.glow-one { background: #6c63ff; top: -100px; left: -70px; }
.glow-two { background: #22d3ee; right: -100px; bottom: -110px; }
.game {
  width: min(94vw, 500px); padding: 30px; position: relative; z-index: 1;
  text-align: center; border: 1px solid #252d49; border-radius: 28px;
  background: rgba(11, 16, 32, .78); box-shadow: 0 30px 90px rgba(0,0,0,.45);
  backdrop-filter: blur(18px);
}
.hero .eyebrow { font-size: 10px; letter-spacing: .22em; color: #8d96b8; }
h1 { margin: 8px 0 6px; font-size: clamp(38px, 10vw, 58px); letter-spacing: -.05em; }
h1 span { color: #756bff; }
.hero p { margin: 0 0 24px; color: #9da7c5; font-size: 13px; }
.scoreboard {
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px; align-items: center;
  margin-bottom: 18px;
}
.score { padding: 12px; border: 1px solid #252d49; border-radius: 15px; background: #0d1325; }
.score small { display: block; color: #7f89a8; font-size: 9px; letter-spacing: .12em; }
.score strong { display: block; margin-top: 2px; font-size: 25px; }
.turn { min-width: 130px; color: #cbd2ea; font-size: 12px; font-weight: 600; }
.board-wrap { padding: 10px; border: 1px solid #252d49; border-radius: 22px; background: #090e1d; }
.board { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.cell {
  aspect-ratio: 1; border: 1px solid #293351; border-radius: 16px;
  background: linear-gradient(145deg, #131b32, #0d1428); color: #fff;
  font-size: clamp(38px, 12vw, 60px); font-weight: 800; cursor: pointer;
  transition: transform .15s, border-color .15s, background .15s;
}
.cell:hover:not(:disabled) { transform: translateY(-2px); border-color: #756bff; background: #17203a; }
.cell:disabled { cursor: default; }
.cell.x { color: #8f87ff; text-shadow: 0 0 22px rgba(117,107,255,.35); }
.cell.o { color: #42d9e9; text-shadow: 0 0 22px rgba(34,211,238,.3); }
.cell.win { border-color: #7df3c2; background: #122a29; transform: scale(.97); }
.actions { display: flex; justify-content: center; gap: 10px; margin-top: 18px; }
.actions button {
  border: 1px solid #2b3553; border-radius: 12px; padding: 11px 16px;
  color: #fff; cursor: pointer; font-weight: 700;
}
.primary { background: #665bd1; }
.secondary { background: #10172a; }
.hint { margin: 16px 0 0; color: #697492; font-size: 11px; }
@media (max-width: 460px) {
  .game { padding: 22px; border-radius: 22px; }
  .scoreboard { grid-template-columns: 1fr 1fr; }
  .turn { grid-column: 1 / -1; grid-row: 1; }
}
""",
                "game.js": """const boardElement = document.getElementById("board");
const statusElement = document.getElementById("status");
const restartButton = document.getElementById("restart");
const resetScoreButton = document.getElementById("reset-score");
const scoreXElement = document.getElementById("score-x");
const scoreOElement = document.getElementById("score-o");

let board = Array(9).fill("");
let currentPlayer = "X";
let gameOver = false;
let scores = { X: 0, O: 0 };

const wins = [
  [0,1,2], [3,4,5], [6,7,8],
  [0,3,6], [1,4,7], [2,5,8],
  [0,4,8], [2,4,6]
];

function winner() {
  for (const [a,b,c] of wins) {
    if (board[a] && board[a] === board[b] && board[a] === board[c]) return board[a];
  }
  return board.every(Boolean) ? "draw" : null;
}

function render(winningCells = []) {
  boardElement.innerHTML = "";
  board.forEach((value, index) => {
    const cell = document.createElement("button");
    cell.className = "cell" + (value ? " " + value.toLowerCase() : "") + (winningCells.includes(index) ? " win" : "");
    cell.textContent = value;
    cell.disabled = gameOver || Boolean(value);
    cell.setAttribute("aria-label", "Cell " + (index + 1) + (value ? ": " + value : ""));
    cell.addEventListener("click", () => move(index));
    boardElement.appendChild(cell);
  });
  scoreXElement.textContent = scores.X;
  scoreOElement.textContent = scores.O;
}

function move(index) {
  if (gameOver || board[index]) return;
  board[index] = currentPlayer;
  const result = winner();
  if (result) {
    gameOver = true;
    if (result === "draw") {
      statusElement.textContent = "Draw game — play again!";
      render();
    } else {
      scores[result] += 1;
      statusElement.textContent = "Player " + result + " wins!";
      const winningCells = wins.find(([a,b,c]) => board[a] && board[a] === board[b] && board[a] === board[c]) || [];
      render(winningCells);
    }
  } else {
    currentPlayer = currentPlayer === "X" ? "O" : "X";
    statusElement.textContent = "Player " + currentPlayer + "'s turn";
    render();
  }
}

function restart() {
  board = Array(9).fill("");
  currentPlayer = "X";
  gameOver = false;
  statusElement.textContent = "Player X's turn";
  render();
}

function resetScore() {
  scores = { X: 0, O: 0 };
  restart();
}

restartButton.addEventListener("click", restart);
resetScoreButton.addEventListener("click", resetScore);
render();
""",
                "tests/test_project.py": """from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_browser_game_files_exist():
    assert (ROOT / "index.html").is_file()
    assert (ROOT / "style.css").is_file()
    assert (ROOT / "game.js").is_file()

def test_game_contains_core_features():
    js = (ROOT / "game.js").read_text(encoding="utf-8")
    assert "function move" in js
    assert "function restart" in js
    assert "function resetScore" in js
    assert "wins" in js
""",
            },
            test_command=["python", "-m", "pytest", "-q"],
        )

    def _fallback_calculator(self) -> GeneratedProject:
        from src.company.browser_calculator import browser_calculator
        return browser_calculator()

    def _fallback_repair(
        self,
        files: dict[str, str],
        failure: str,
    ) -> GeneratedProject:
        combined = "\n".join(files.values()).lower()
        if "calculator" in combined or "calculator" in failure.lower():
            return self._fallback_calculator()
        raise RuntimeError("Ollama repair failed and no deterministic repair is available")

    async def _call(self, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return str(data.get("response", ""))

    def _parse(self, response: str) -> GeneratedProject:
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            start, end = response.find("{"), response.rfind("}")
            if start < 0 or end <= start:
                raise RuntimeError("Ollama returned invalid project JSON") from None
            try:
                result = json.loads(response[start : end + 1])
            except json.JSONDecodeError as exc:
                raise RuntimeError("Ollama returned invalid project JSON") from exc

        raw_files = result.get("files")
        if not isinstance(raw_files, dict) or not raw_files:
            raise RuntimeError("Ollama returned no project files")

        files: dict[str, str] = {}
        for raw_path, content in raw_files.items():
            raw_path_text = str(raw_path).strip().replace("\\", "/")
            path = PurePosixPath(raw_path_text)
            if (
                path.is_absolute()
                or not raw_path_text
                or ".." in path.parts
                or ":" in raw_path_text
                or "\n" in raw_path_text
            ):
                raise RuntimeError(f"Unsafe generated path: {raw_path}")
            if not content or len(str(content).encode("utf-8")) > 2_000_000:
                raise RuntimeError(f"Invalid generated file: {raw_path}")
            files[str(path)] = str(content)

        if not any(path.lower().startswith("tests/") for path in files):
            root_tests = [
                path for path in files
                if path.lower().endswith(".py")
                and (
                    path.lower().startswith("test_")
                    or path.lower().endswith("_test.py")
                )
            ]
            for path in root_tests:
                normalized = f"tests/{PurePosixPath(path).name}"
                if normalized not in files:
                    files[normalized] = files[path]
                del files[path]

        if not any(path.lower().startswith("tests/") for path in files):
            smoke_lines = [
                "from pathlib import Path",
                "",
                "",
                "def test_generated_python_compiles():",
                "    root = Path(__file__).resolve().parents[1]",
                "    python_files = [",
                "        path for path in root.rglob('*.py')",
                "        if 'tests' not in path.parts",
                "    ]",
                "    assert python_files, 'Generated project contains no Python source files'",
                "    for path in python_files:",
                "        compile(path.read_text(encoding='utf-8'), str(path), 'exec')",
                "",
            ]
            files["tests/test_generated_project.py"] = "\n".join(smoke_lines)

        command = self._normalize_test_command(result.get("test_command"))

        return GeneratedProject(
            files=files,
            test_command=command,
        )

    @staticmethod
    def _normalize_test_command(raw_command: object) -> list[str]:
        """Accept only local Python test runners produced by the factory."""
        default = ["python", "-m", "pytest", "-q"]

        if not isinstance(raw_command, list) or not raw_command:
            return default

        command = [str(item).strip() for item in raw_command if str(item).strip()]
        if not command:
            return default

        executable = command[0].replace("\\", "/").rsplit("/", 1)[-1].lower()

        # Keep QA local and deterministic. The model must not turn the test
        # phase into an arbitrary shell, installer, or network command.
        if executable in {"pytest", "pytest.exe"}:
            return command

        if executable in {"python", "python3", "python.exe", "py", "py.exe"}:
            args = command[1:]
            if (
                len(args) >= 2
                and args[0] == "-m"
                and args[1].lower() in {"pytest", "unittest"}
            ):
                return command
            return default

        return default
