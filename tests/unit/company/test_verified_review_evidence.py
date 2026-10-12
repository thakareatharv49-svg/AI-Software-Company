from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.company import review_routes
from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.company.mission_jobs import MissionJobStatus
from src.company.review_workflow import ProductReview, Requirement


def test_factory_evidence_is_derived_from_real_runner_results():
    result = SimpleNamespace(
        pipeline=SimpleNamespace(
            qa_result=SimpleNamespace(status="passed", exit_code=0, duration_ms=321),
            review_result=SimpleNamespace(
                status="approved",
                approved=True,
                summary="No blocking security findings.",
            ),
        )
    )

    evidence = FactoryAutonomousRunner._quality_evidence_updates(
        result, ["python", "-m", "pytest", "-q"]
    )

    assert evidence["qa_status"] == "passed"
    assert evidence["qa_exit_code"] == 0
    assert evidence["qa_duration_ms"] == 321
    assert evidence["qa_command"] == ["python", "-m", "pytest", "-q"]
    assert "status=passed" in evidence["qa_evidence"]
    assert "approved=True" in evidence["security_evidence"]
    assert "No blocking security findings." in evidence["security_evidence"]


def _completed_job(plan):
    return SimpleNamespace(
        status=MissionJobStatus.COMPLETED,
        mission=SimpleNamespace(name="Demo"),
        plan=plan,
    )


def test_review_submission_rejects_missing_factory_evidence(tmp_path, monkeypatch):
    products = tmp_path / "generated-products"
    (products / "mission-123").mkdir(parents=True)
    monkeypatch.setattr(review_routes, "PRODUCTS_ROOT", products)
    monkeypatch.setattr(
        review_routes,
        "_get_job",
        lambda mission_id, center: _completed_job(
            SimpleNamespace(
                qa_status=None,
                qa_evidence=None,
                security_status=None,
                security_evidence=None,
            )
        ),
    )

    payload = review_routes.SubmitReviewRequest(
        requirements=[Requirement(description="Core workflow works")],
        qa_evidence="Fake caller-supplied QA passed",
        security_evidence="Fake caller-supplied security passed",
    )
    with pytest.raises(HTTPException) as exc:
        review_routes.submit_product_for_review("mission-123", payload, None)

    assert exc.value.status_code == 409
    assert "factory QA run" in exc.value.detail


def test_review_submission_uses_server_evidence_not_caller_text(tmp_path, monkeypatch):
    products = tmp_path / "generated-products"
    (products / "mission-123").mkdir(parents=True)
    monkeypatch.setattr(review_routes, "PRODUCTS_ROOT", products)
    monkeypatch.setattr(
        review_routes,
        "_get_job",
        lambda mission_id, center: _completed_job(
            SimpleNamespace(
                qa_status="passed",
                qa_evidence="Factory QA runner: status=passed; exit_code=0; duration_ms=321",
                security_status="approved",
                security_evidence="Factory security reviewer: status=approved; approved=True",
            )
        ),
    )
    review = ProductReview(mission_id="mission-123")
    monkeypatch.setattr(review_routes, "_get_review", lambda mission_id, center: review)

    class Store:
        saved = None

        def save(self, value):
            self.saved = value

    store = Store()
    monkeypatch.setattr(review_routes, "_review_store", lambda: store)
    payload = review_routes.SubmitReviewRequest(
        requirements=[Requirement(description="Core workflow works")],
        qa_evidence="Caller says tests passed (not trusted)",
        security_evidence="Caller says secure (not trusted)",
    )

    updated = review_routes.submit_product_for_review("mission-123", payload, None)

    assert updated.qa_evidence.startswith("Factory QA runner:")
    assert updated.security_evidence.startswith("Factory security reviewer:")
    assert "not trusted" not in updated.qa_evidence
    assert "not trusted" not in updated.security_evidence
    assert store.saved == updated
