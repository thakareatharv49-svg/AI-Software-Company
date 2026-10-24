from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "large_project_benchmark_cases.json"
DEFAULT_OUTPUT = Path("artifacts/m86-large-project-benchmark-results.json")
TERMINAL_STATES = {"completed", "failed", "blocked", "cancelled"}
MAX_RESPONSE_BYTES = 2_000_000


class BenchmarkError(RuntimeError):
    """Raised when the benchmark cannot safely communicate with the factory."""


class FactoryApi:
    """Small standard-library client for the running company's real factory API."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        token = os.getenv("AI_SOFTWARE_COMPANY_BEARER_TOKEN", "").strip()
        cookie = os.getenv("AI_SOFTWARE_COMPANY_AUTH_COOKIE", "").strip()
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        if cookie:
            self.headers["Cookie"] = cookie

    def request(self, method: str, path: str, *, query: dict[str, object] | None = None,
                body: dict[str, object] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url, data=data, headers=self.headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise BenchmarkError(f"Factory API response exceeded {MAX_RESPONSE_BYTES} bytes")
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            raise BenchmarkError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BenchmarkError(f"{method} {path} failed: {exc}") from exc

    def run_case(self, case: dict[str, Any], *, max_retries: int,
                 poll_interval: float, deadline_seconds: float) -> dict[str, Any]:
        started = time.monotonic()
        started_at = datetime.now(UTC).isoformat()
        result: dict[str, Any] = {
            "case_id": case["id"], "project_type": case["project_type"],
            "status": "failed", "started_at": started_at, "mission_id": None,
            "duration_ms": 0, "retries": 0, "stages": [], "checks": [],
            "test_command": list(case["test_command"]), "test_command_evidence": None,
            "artifact_files": [], "errors": [],
        }
        try:
            record = self.request("POST", "/api/missions", body={
                "name": f"M86 {case['id']} {datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
                "objective": case["mission"],
                "constraints": [
                    "M86 benchmark: implement the complete requested product, not a demo.",
                    "Keep all generated files within the mission workspace.",
                    "Run the project's declared tests and preserve real exit-code evidence.",
                    f"Required capabilities: {', '.join(case['required_features'])}.",
                ],
            })
            mission = record.get("mission", {}) if isinstance(record, dict) else {}
            mission_id = mission.get("id")
            if not isinstance(mission_id, str) or not mission_id:
                raise BenchmarkError("Mission submission response did not contain mission.id")
            result["mission_id"] = mission_id

            # This endpoint runs the queued mission through ProjectFactory and the
            # configured autonomous runner. It is intentionally not a mock/simulation.
            self.request("POST", f"/api/missions/{mission_id}/factory-run",
                         query={"max_retries": max_retries})
            deadline = time.monotonic() + deadline_seconds
            job: dict[str, Any] = {}
            while time.monotonic() < deadline:
                job_response = self.request("GET", f"/api/missions/{mission_id}/job")
                job = job_response if isinstance(job_response, dict) else {}
                status = _status(job.get("status"))
                if status in TERMINAL_STATES:
                    break
                time.sleep(poll_interval)
            else:
                result["errors"].append(f"Mission did not reach a terminal state within {deadline_seconds:g}s")
                result["status"] = "timeout"

            if result["status"] != "timeout":
                status = _status(job.get("status"))
                result["status"] = status or "failed"
                result["retries"] = _nonnegative_int(job.get("attempts", job.get("retry_count", 0)))
                plan = job.get("plan") if isinstance(job.get("plan"), dict) else {}
                result["stages"] = _stage_evidence(plan)
                result["test_command_evidence"] = _test_evidence(plan)
                diagnostics = self.request("GET", f"/api/missions/{mission_id}/diagnostics")
                result["diagnostics"] = _safe_diagnostics(diagnostics)
                audit = self.request("GET", f"/api/missions/{mission_id}/audit")
                result["audit_event_count"] = len(audit) if isinstance(audit, list) else 0
                outputs = self.request("GET", f"/api/missions/{mission_id}/outputs")
                result["outputs"] = [
                    {key: item.get(key) for key in ("name", "status", "output_type", "repository", "product_url")}
                    for item in outputs if isinstance(item, dict)
                ] if isinstance(outputs, list) else []
                workspace = _find_workspace(mission_id)
                files = _workspace_files(workspace) if workspace else []
                result["artifact_files"] = files
                result["checks"] = evaluate_case(case, files, plan, status)
        except BenchmarkError as exc:
            result["errors"].append(str(exc))
        except Exception as exc:  # keep a structured record for unexpected per-case errors
            result["errors"].append(f"{type(exc).__name__}: {exc}")
        finally:
            result["duration_ms"] = max(0, int((time.monotonic() - started) * 1000))
        return result


def _status(value: object) -> str:
    raw = getattr(value, "value", value)
    return raw.casefold() if isinstance(raw, str) else ""


def _nonnegative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def _stage_evidence(plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        return []
    evidence = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        evidence.append({
            "name": step.get("name") or step.get("title") or step.get("id"),
            "status": _status(step.get("status")) or "unknown",
            "attempts": _nonnegative_int(step.get("attempts", 0)),
            "error": str(step.get("error") or step.get("last_error") or "")[:1000] or None,
        })
    return evidence


def _test_evidence(plan: dict[str, Any]) -> dict[str, Any] | None:
    keys = (
        "qa_status", "qa_exit_code", "qa_duration_ms", "qa_command",
        "qa_stdout", "qa_stderr", "quality_evidence",
    )
    found = {key: plan[key] for key in keys if key in plan}
    if not found:
        return None
    for key in ("qa_stdout", "qa_stderr"):
        if key in found:
            found[key] = str(found[key])[-4000:]
    return found


def _find_workspace(mission_id: str) -> Path | None:
    # Match the factory's configured output root and the legacy workspace location,
    # but only accept a direct child whose resolved path stays under the root.
    roots = [
        Path("generated-products"),
        Path(os.getenv("AI_SOFTWARE_COMPANY_WORKSPACES", "/tmp/ai-software-company-workspaces")),
    ]
    for root in roots:
        try:
            resolved_root = root.resolve()
            candidate = (resolved_root / mission_id).resolve()
            candidate.relative_to(resolved_root)
        except (OSError, ValueError):
            continue
        if candidate.is_dir():
            return candidate
    return None


def _workspace_files(workspace: Path) -> list[str]:
    files: list[str] = []
    for path in workspace.rglob("*"):
        if path.is_file() and not any(part in {".git", "__pycache__", ".venv", "node_modules"} for part in path.parts):
            relative = path.relative_to(workspace).as_posix()
            safe = PurePosixPath(relative)
            if not safe.is_absolute() and ".." not in safe.parts:
                files.append(relative)
    return sorted(files)


def evaluate_case(case: dict[str, Any], files: list[str], plan: dict[str, Any],
                  mission_status: str) -> list[dict[str, Any]]:
    file_set = set(files)
    required_files = list(case.get("expected_files", []))
    missing = [path for path in required_files if path not in file_set]
    all_text = ""
    # Only inspect bounded, ordinary text files under the mission workspace.
    workspace = _find_workspace(str(plan.get("mission_id", ""))) if plan.get("mission_id") else None
    if workspace:
        chunks = []
        for relative in files:
            path = workspace / relative
            try:
                if path.stat().st_size <= 250_000:
                    chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
        all_text = "\n".join(chunks).casefold()
    checks = [
        {"id": "factory_terminal_success", "passed": mission_status == "completed",
         "detail": f"Factory mission status: {mission_status or 'unknown'}"},
        {"id": "required_files", "passed": not missing,
         "detail": "All expected files are present." if not missing else f"Missing expected files: {missing}"},
        {"id": "required_features", "passed": bool(all_text) and all(feature.casefold() in all_text for feature in case.get("required_features", [])),
         "detail": "Textual feature markers found." if all_text and all(feature.casefold() in all_text for feature in case.get("required_features", []))
         else "Feature markers not all found; this heuristic is diagnostic, not a semantic quality judgment."},
        {"id": "test_command_exit_code", "passed": _test_exit_code(plan) == 0,
         "detail": f"Recorded QA exit code: {_test_exit_code(plan)!r}"},
    ]
    return checks


def _test_exit_code(plan: dict[str, Any]) -> int | None:
    for key in ("qa_exit_code", "test_exit_code"):
        value = plan.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    evidence = plan.get("quality_evidence")
    if isinstance(evidence, dict):
        for key in ("qa_exit_code", "test_exit_code", "exit_code"):
            value = evidence.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _safe_diagnostics(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = ("diagnosis", "recommended_action", "queue_wait_seconds",
            "heartbeat_stale", "current_step", "failed_steps")
    return {key: value[key] for key in keys if key in value}


def load_catalog(path: Path) -> list[dict[str, Any]]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkError(f"Cannot load benchmark catalog {path}: {exc}") from exc
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        raise BenchmarkError("Unsupported benchmark catalog schema_version")
    cases = catalog.get("cases")
    if not isinstance(cases, list) or not cases:
        raise BenchmarkError("Benchmark catalog has no cases")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise BenchmarkError("Every benchmark case must be an object with a string id")
        if case["id"] in seen:
            raise BenchmarkError(f"Duplicate benchmark case id: {case['id']}")
        seen.add(case["id"])
        for path_value in case.get("expected_files", []):
            path = PurePosixPath(path_value)
            if path.is_absolute() or ".." in path.parts or chr(92) in path_value:
                raise BenchmarkError(f"Unsafe expected artifact path in {case['id']}: {path_value}")
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run M86 cases through the real AI Software Company factory API.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-url", default=os.getenv("AI_SOFTWARE_COMPANY_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--case", action="append", dest="case_ids", help="Case id to run; repeat to select multiple.")
    parser.add_argument("--timeout", type=float, default=3600.0, help="Per-mission deadline in seconds.")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args(argv)
    if args.timeout <= 0 or args.poll_interval <= 0 or not 0 <= args.max_retries <= 5:
        parser.error("timeout/poll interval must be positive and max retries must be 0..5")
    try:
        cases = load_catalog(args.catalog)
        if args.case_ids:
            requested = set(args.case_ids)
            unknown = requested - {case["id"] for case in cases}
            if unknown:
                parser.error(f"Unknown case id(s): {', '.join(sorted(unknown))}")
            cases = [case for case in cases if case["id"] in requested]
        api = FactoryApi(args.base_url, timeout=min(60.0, args.timeout))
        results = []
        for case in cases:
            results.append(api.run_case(case, max_retries=args.max_retries,
                                        poll_interval=args.poll_interval,
                                        deadline_seconds=args.timeout))
        summary = {
            "schema_version": 1,
            "started_at": datetime.now(UTC).isoformat(),
            "base_url": args.base_url.rstrip("/"),
            "case_count": len(results),
            "passed_cases": sum(item["status"] == "completed" and all(check.get("passed") for check in item["checks"]) for item in results),
            "results": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({key: summary[key] for key in ("case_count", "passed_cases")}, indent=2))
        print(f"Evidence written to {args.output}")
        return 0 if summary["passed_cases"] == summary["case_count"] else 1
    except BenchmarkError as exc:
        print(f"M86 benchmark error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
