import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.company.browser_calculator import browser_calculator
from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter, MissionSubmission
from src.company.models.contracts import CompanyState
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.main import app


def test_submit_mission_queues_company_work() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    record = center.submit_mission(
        MissionSubmission(name="Build X", objective="Create X for users")
    )
    assert record.status == "queued"
    assert record.mission.objective == "Create X for users"
    assert center.state.status.value == "idle"
    assert [step.stage.value for step in record.plan.steps] == [
        "research", "product", "architecture", "tasks", "agents", "execution",
        "qa", "security", "github", "deployment", "monitoring", "learning",
    ]


def test_queued_company_accepts_multiple_missions() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    first = center.submit_mission(MissionSubmission(name="First", objective="First objective"))
    second = center.submit_mission(MissionSubmission(name="Second", objective="Second objective"))
    assert first.status == "queued"
    assert second.status == "queued"


@pytest.mark.asyncio
async def test_explicit_factory_launch_prioritizes_selected_mission() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    # This test covers priority ordering, not restoration of pending jobs from
    # previous local runs. Start with only the missions created below.
    center._factory.queue.clear()
    older = center.submit_mission(
        MissionSubmission(name="Restored mission", objective="Run older work")
    )
    center.enqueue_factory_mission(older.mission.id)
    requested = center.submit_mission(
        MissionSubmission(name="Requested mission", objective="Run this now")
    )
    center.enqueue_factory_mission(requested.mission.id)
    selected: list[str] = []
    queue_at_start: list[str] = []

    async def fake_run(**kwargs):
        queue_at_start.extend(item.mission.id for item in center._factory.queue)
        selected.append(center._factory.queue[0].mission.id)

    center._factory.run = fake_run
    await center.run_factory(max_projects=1, mission_id=requested.mission.id)
    assert center._factory_task is not None
    await center._factory_task
    assert selected == [requested.mission.id]
    assert queue_at_start == [requested.mission.id, older.mission.id]


def test_control_api_serves_mission_and_app() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post("/api/missions", json={"name": "Build X", "objective": "Create X"})
        assert response.status_code == 201
        assert response.json()["status"] == "queued"
        assert client.get("/api/company/state").json()["status"] == "idle"
        assert client.get("/app").status_code == 200
        assert "AI Software Company" in client.get("/app").text
    finally:
        app.dependency_overrides.clear()


def test_stop_control_changes_company_state() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    center.submit_mission(MissionSubmission(name="Build X", objective="Create X"))
    state = center.stop()
    assert isinstance(state, CompanyState)
    assert state.status.value == "stopped"


def test_mission_plan_api_exposes_internal_pipeline() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Build X", "objective": "Create X"},
        )
        mission_id = response.json()["mission"]["id"]
        plan = client.get(f"/api/missions/{mission_id}/plan")
        assert plan.status_code == 200
        assert len(plan.json()["steps"]) == 12
        assert plan.json()["steps"][0]["stage"] == "research"
    finally:
        app.dependency_overrides.clear()


def test_mission_job_api_exposes_persistent_lifecycle() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Lifecycle API", "objective": "Expose job state"},
        )
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]

        job = client.get(f"/api/missions/{mission_id}/job")
        assert job.status_code == 200
        assert job.json()["id"] == mission_id
        assert job.json()["status"] == "queued"

        jobs = client.get("/api/mission-jobs")
        assert jobs.status_code == 200
        assert any(item["id"] == mission_id for item in jobs.json())
    finally:
        app.dependency_overrides.clear()


def test_mission_cancel_and_retry_api() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Recovery API", "objective": "Exercise recovery controls"},
        )
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]

        cancelled = client.post(f"/api/missions/{mission_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        center._job_store.save(
            center.mission_job(mission_id).model_copy(
                update={"status": "blocked", "message": "blocked for retry"}
            )
        )
        retried = client.post(f"/api/missions/{mission_id}/retry")
        assert retried.status_code == 200
        assert retried.json()["status"] == "queued"
    finally:
        app.dependency_overrides.clear()


def test_mission_audit_api_supports_filters() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Audit API", "objective": "Inspect lifecycle history"},
        )
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]
        audit = client.get(
            f"/api/missions/{mission_id}/audit",
            params={"event_type": "MISSION_CREATED", "status": "queued"},
        )
        assert audit.status_code == 200
        assert isinstance(audit.json(), list)
        missing = client.get("/api/missions/missing/audit")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_project_outputs_api() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Outputs API", "objective": "Expose project outputs"},
        )
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]
        outputs = client.get(f"/api/missions/{mission_id}/outputs")
        assert outputs.status_code == 200
        assert outputs.json() == []
        assert client.get("/api/missions/missing/outputs").status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_factory_run_api_starts_the_requested_mission() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    started: list[str] = []

    async def fake_run(**kwargs):
        started.append(center._factory.queue[0].mission.id)

    center._factory.run = fake_run
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/api/missions",
                json={"name": "Route launch", "objective": "Verify factory route execution"},
            )
            assert created.status_code == 201
            mission_id = created.json()["mission"]["id"]

            launched = await client.post(f"/api/missions/{mission_id}/factory-run")
            assert launched.status_code == 200
            assert launched.json() == {"status": "started", "mission_id": mission_id}
            assert center._factory_task is not None
            await center._factory_task

        assert started == [mission_id]
    finally:
        app.dependency_overrides.clear()


def test_browser_calculator_fallback_emits_valid_python() -> None:
    generated = browser_calculator()
    assert {"index.html", "style.css", "app.js", "calculator.py", "tests/test_calculator.py"} <= set(
        generated.files
    )
    compile(generated.files["calculator.py"], "calculator.py", "exec")
    compile(generated.files["tests/test_calculator.py"], "test_calculator.py", "exec")


def test_dashboard_completed_product_preview_uses_defined_identifier() -> None:
    from pathlib import Path

    dashboard = (
        Path(__file__).resolve().parents[3] / "src" / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")

    assert "const hasBrowserPreviewAfterRefresh = productIds.has(id);" in dashboard
    assert "hasBrowserPreviewAfterRefreshAfterRefresh" not in dashboard
    assert "job.status === \"completed\" && hasBrowserPreviewAfterRefresh" in dashboard

    static_dir = Path(__file__).resolve().parents[3] / "src" / "web" / "static"
    html = (static_dir / "index.html").read_text(encoding="utf-8")
    css = (static_dir / "styles.css").read_text(encoding="utf-8")

    assert '/app/static/app.js?v=12' in html
    assert '/app/static/styles.css?v=7' in html
    assert 'href="#missions-section"' in html and 'id="missions-section"' in html
    assert 'href="#factory-section"' in html and 'id="factory-section"' in html
    assert ".nav a{" in css
