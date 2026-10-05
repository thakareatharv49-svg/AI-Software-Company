from company.evaluation import BenchmarkCase, CompanyEvaluator


def test_evaluator_scores_cases_and_categories() -> None:
    cases = (
        BenchmarkCase("coding", "coding", True),
        BenchmarkCase("qa", "qa", True),
        BenchmarkCase("research", "research", False),
    )
    report = CompanyEvaluator().evaluate(
        cases,
        {"coding": True, "qa": True, "research": True},
    )
    assert report.score == 2 / 3
    assert report.category_scores() == {"coding": 1.0, "qa": 1.0, "research": 0.0}


def test_regression_gate_blocks_score_drop() -> None:
    evaluator = CompanyEvaluator()
    report = evaluator.evaluate(
        (BenchmarkCase("case", "runtime", True),),
        {"case": False},
    )
    assert not evaluator.regression_gate(report, 1.0)
