from company.learning.engine import LearningEngine


def test_learning_engine_analyzes_success_and_failure() -> None:
    report = LearningEngine().analyze_executions(
        [{"success": True}, {"success": True}, {"success": False}]
    )

    assert report.signals[0].subject == "execution_success_rate"
    assert report.signals[0].score == 2 / 3
    assert any(signal.category == "failure_analysis" for signal in report.signals)


def test_learning_engine_evaluates_agents() -> None:
    report = LearningEngine().evaluate_agent_performance(
        {"researcher": [True, True], "builder": [True, False]}
    )

    assert report.signals[0].subject == "builder"
    assert report.signals[1].subject == "researcher"


def test_learning_engine_consolidates_without_duplicates() -> None:
    engine = LearningEngine()
    first = engine.analyze_executions([{"success": True}])
    second = engine.analyze_executions([{"success": True}])

    assert engine.consolidate((first, second)) == (
        "Observed 1 executions with success rate 1.00.",
    )


def test_empty_learning_input_is_safe() -> None:
    report = LearningEngine().analyze_executions([])
    assert report.signals == ()
    assert report.consolidated_knowledge == ()
