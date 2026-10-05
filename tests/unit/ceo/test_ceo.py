from company.ceo import (
    AICEO,
    DecisionEngine,
    DecisionType,
    Mission,
    MissionPlan,
    MissionPlanner,
    MissionStatus,
)


def test_mission_is_received():
    ceo = AICEO()

    mission = ceo.receive(
        Mission(
            mission_id="m-001",
            objective="Build an autonomous software project",
        )
    )

    assert mission.status == MissionStatus.RECEIVED
    assert mission.mission_id == "m-001"


def test_planner_creates_executable_plan():
    planner = MissionPlanner()

    plan = planner.plan(
        Mission(
            mission_id="m-002",
            objective="Build an autonomous software project",
        )
    )

    assert plan.mission_id == "m-002"
    assert plan.objective == "Build an autonomous software project"
    assert len(plan.goals) >= 1
    assert len(plan.tasks) >= 1


def test_planner_preserves_constraints_as_risks():
    planner = MissionPlanner()

    plan = planner.plan(
        Mission(
            mission_id="m-003",
            objective="Build a project",
            constraints=("No paid APIs", "Must pass tests"),
        )
    )

    assert plan.risks == ("No paid APIs", "Must pass tests")


def test_decision_engine_accepts_valid_plan():
    engine = DecisionEngine()

    plan = MissionPlan(
        mission_id="m-004",
        objective="Build a project",
        goals=("Define success",),
        tasks=("Implement", "Test"),
    )

    decision = engine.decide(plan)

    assert decision.decision_type == DecisionType.ACCEPT
    assert decision.confidence == 1.0
    assert decision.requires_human is False


def test_decision_engine_rejects_empty_plan():
    engine = DecisionEngine()

    plan = MissionPlan(
        mission_id="m-005",
        objective="Build a project",
        goals=(),
        tasks=(),
    )

    decision = engine.decide(plan)

    assert decision.decision_type == DecisionType.REJECT


def test_ceo_evaluates_mission():
    ceo = AICEO()

    result = ceo.evaluate(
        Mission(
            mission_id="m-006",
            objective="Create a secure autonomous project factory",
        )
    )

    assert result.mission.status == MissionStatus.APPROVED
    assert result.decision.decision_type == DecisionType.ACCEPT
    assert result.plan.mission_id == "m-006"


def test_ceo_rejects_invalid_mission():
    ceo = AICEO()

    try:
        ceo.evaluate(
            Mission(
                mission_id="m-007",
                objective="",
            )
        )
    except ValueError as exc:
        assert "objective" in str(exc).lower()
    else:
        raise AssertionError("Expected invalid mission to fail")
