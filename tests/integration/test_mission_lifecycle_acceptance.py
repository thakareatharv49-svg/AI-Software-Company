from fastapi.testclient import TestClient

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.main import app
from src.security.authorization import require_company_owner


def test_mission_lifecycle_acceptance_from_submission_to_safe_cancellation():
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    app.dependency_overrides[require_company_owner] = lambda: None
    try:
        client = TestClient(app)
        created = client.post(
            "/api/missions",
            json={
                "name": "Lifecycle acceptance",
                "objective": "Build a reliable workspace with saved records and automated tests.",
                "constraints": ["Keep generated files local"],
            },
        )
        assert created.status_code == 201
        mission_id = created.json()["mission"]["id"]

        job = client.get(f"/api/missions/{mission_id}/job")
        assert job.status_code == 200
        assert job.json()["status"] == "queued"

        plan = client.get(f"/api/missions/{mission_id}/plan")
        assert plan.status_code == 200
        assert len(plan.json()["acceptance_criteria"]) >= 2
        assert len(plan.json()["engineering_tasks"]) >= 6

        validation = client.get(f"/api/missions/{mission_id}/plan/validation")
        assert validation.status_code == 200
        assert validation.json()["valid"] is True
        assert validation.json()["stage_count"] == 12
        assert validation.json()["engineering_task_count"] >= 6

        diagnostics = client.get(f"/api/missions/{mission_id}/diagnostics")
        assert diagnostics.status_code == 200
        assert diagnostics.json()["mission_id"] == mission_id

        cancelled = client.post(f"/api/missions/{mission_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        final_job = client.get(f"/api/missions/{mission_id}/job")
        assert final_job.status_code == 200
        assert final_job.json()["status"] == "cancelled"
        final_diagnostics = client.get(f"/api/missions/{mission_id}/diagnostics")
        assert final_diagnostics.status_code == 200
        assert final_diagnostics.json()["diagnosis"] == "cancelled"
    finally:
        app.dependency_overrides.clear()


# M84 deterministic public-path acceptance harness

import json
import sys
from types import SimpleNamespace

from src.agents.models.contracts import AgentDefinition, AgentResult
from src.agents.models.enums import AgentPermission
from src.agents.registry.registry import AgentRegistry
from src.company.execution.pipeline import CompanyExecutionPipeline
from src.memory.service.service import MemoryService
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission as PipelineMission, TaskPlanItem
from src.projects.engine.project_engine import ProjectEngine
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.execution.runner import QARunner
from src.qa.models.contracts import QATestRequest
from src.security.review.reviewer import CodeReviewer


class _DeterministicEngineer:
    async def __call__(self, request):
        return AgentResult(
            task_id=request.task_id,
            agent_name="engineer",
            success=True,
            output="Deterministic acceptance adapter executed the requested task.",
        )


class _RealPipelineMissionRunner:
    """Keep the factory path real while replacing only nondeterministic model calls."""

    def __init__(self, workspace):
        self.workspace = workspace
        self.pipeline_result = None

    async def run(self, mission, plan, on_progress=None):
        registry = AgentRegistry()
        registry.register(
            AgentDefinition(
                name="engineer",
                role="software engineer",
                capabilities=["coding"],
                permissions={AgentPermission.READ_FILES, AgentPermission.WRITE_FILES},
            )
        )
        pipeline = CompanyExecutionPipeline(
            project_engine=ProjectEngine(),
            manager=MasterManager(agent_registry=registry),
            qa_runner=QARunner(),
            reviewer=CodeReviewer(),
            memory=MemoryService(),
        )
        files = {
            "index.html": (
                "<!doctype html><html><head><title>Lifecycle Product</title>"
                "<link rel=\"stylesheet\" href=\"style.css\"></head>"
                "<body><main><h1>Lifecycle Product</h1><p id=\"status\">Ready</p>"
                "</main><script src=\"app.js\"></script></body></html>"
            ),
            "style.css": "body { font-family: sans-serif; } main { max-width: 48rem; margin: auto; }\n",
            "app.js": "document.querySelector('#status').textContent = 'Ready';\n",
            "tests/test_generated_product.py": (
                "from pathlib import Path\n"
                "def test_generated_product_has_required_files():\n"
                "    assert Path('index.html').is_file()\n"
                "    assert Path('app.js').is_file()\n"
                "    assert 'Lifecycle Product' in Path('index.html').read_text(encoding='utf-8')\n"
            ),
        }
        tests_dir = self.workspace / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_generated_product.py").write_text(
            files["tests/test_generated_product.py"], encoding="utf-8"
        )
        result = await pipeline.run_end_to_end(
            project_request=ProjectCreateRequest(
                name=mission.name,
                description="Deterministic M84 end-to-end acceptance product.",
                objective=mission.objective,
            ),
            mission=PipelineMission(
                name=mission.name,
                objective=mission.objective,
                project_id="m84-acceptance",
            ),
            tasks=[
                TaskPlanItem(
                    title="Implement the product acceptance slice",
                    description=mission.objective,
                    priority="high",
                )
            ],
            qa_request=QATestRequest(
                command=[sys.executable, "-m", "pytest", "-q"],
                working_directory=str(self.workspace),
            ),
            files=files,
            agent_executor=_DeterministicEngineer(),
        )
        self.pipeline_result = result
        if on_progress is not None:
            on_progress(plan)
        return SimpleNamespace(
            pipeline=result,
            stages=[SimpleNamespace(status="completed") for _ in plan.steps],
        )


def test_m84_public_mission_path_reaches_real_qa_and_review_with_trace(tmp_path):
    """Submit via HTTP, execute through the factory, and verify QA/review evidence."""
    center = CompanyControlCenter(CompanyOrchestrator())
    runner = _RealPipelineMissionRunner(tmp_path)
    center._factory.autonomous_runner = runner
    app.dependency_overrides[get_control_center] = lambda: center
    app.dependency_overrides[require_company_owner] = lambda: None
    try:
        client = TestClient(app)
        created = client.post(
            "/api/missions",
            json={
                "name": "M84 lifecycle acceptance",
                "objective": "Build a tiny accessible product and verify its files with executed tests.",
                "constraints": ["Use deterministic local test adapters", "Do not publish to GitHub"],
            },
        )
        assert created.status_code == 201, created.text
        mission_id = created.json()["mission"]["id"]

        queued = client.get(f"/api/missions/{mission_id}/job")
        assert queued.status_code == 200
        assert queued.json()["status"] == "queued"
        plan = client.get(f"/api/missions/{mission_id}/plan")
        assert plan.status_code == 200
        assert len(plan.json()["steps"]) == 12

        started = client.post(f"/api/missions/{mission_id}/factory-run?max_retries=0")
        assert started.status_code == 200, started.text
        final_job = client.get(f"/api/missions/{mission_id}/job")
        outputs = client.get(f"/api/missions/{mission_id}/outputs")
        audit = client.get(f"/api/missions/{mission_id}/audit")
        result = runner.pipeline_result
        trace = {
            "mission_id": mission_id,
            "factory_run_status": started.json().get("status"),
            "job_status": final_job.json().get("status") if final_job.status_code == 200 else final_job.status_code,
            "stage_statuses": [step["status"] for step in final_job.json()["plan"]["steps"]] if final_job.status_code == 200 else [],
            "qa_status": result.qa_result.status.value if result else None,
            "qa_exit_code": result.qa_result.exit_code if result else None,
            "review_status": result.review_result.status.value if result else None,
            "output_statuses": [item["status"] for item in outputs.json()] if outputs.status_code == 200 else [],
            "audit_events": [item["event_type"] for item in audit.json()] if audit.status_code == 200 else [],
        }
        trace_text = json.dumps(trace, sort_keys=True)
        assert final_job.status_code == 200, trace_text
        assert final_job.json()["status"] == "completed", trace_text
        assert all(status == "completed" for status in trace["stage_statuses"]), trace_text
        assert result is not None, trace_text
        assert result.qa_result.status.value == "passed", trace_text
        assert result.qa_result.exit_code == 0, trace_text
        assert result.qa_result.stdout.strip(), trace_text
        assert result.review_result.status.value == "approved", trace_text
        assert (tmp_path / "index.html").is_file(), trace_text
        assert (tmp_path / "app.js").is_file(), trace_text
        assert outputs.status_code == 200 and outputs.json(), trace_text
        assert any(event in trace["audit_events"] for event in ("MISSION_RUNNING", "MISSION_COMPLETED")), trace_text
    finally:
        app.dependency_overrides.clear()
