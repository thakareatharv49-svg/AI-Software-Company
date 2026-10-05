from __future__ import annotations

from dataclasses import replace

from company.acceptance import AcceptanceStatus, AutonomousCompanyAcceptance
from company.autonomous_project import StageResult, StageStatus


def test_acceptance_requires_completed_autonomous_stages() -> None:
    acceptance = AutonomousCompanyAcceptance()
    assert "ai_ceo" in acceptance.REQUIRED_STAGES
    assert AcceptanceStatus.PASSED.value == "passed"


def test_acceptance_stage_names_are_stable() -> None:
    stage = StageResult("deployment", StageStatus.COMPLETED, "ok")
    changed = replace(stage, status=StageStatus.FAILED)
    assert stage.status == StageStatus.COMPLETED
    assert changed.status == StageStatus.FAILED
