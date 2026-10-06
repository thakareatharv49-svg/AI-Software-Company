from company.product_evolution import (
    ContinuousImprovement,
    Experiment,
    ExperimentService,
    FeatureCandidate,
    FeaturePrioritizer,
    Feedback,
    FeedbackIntelligence,
    ProductIterationService,
    VariantResult,
)


def test_m91_iteration_plan():
    assert ProductIterationService().plan("app", "v2", ["search"]).status == "planned"


def test_m92_feedback_intelligence():
    result = FeedbackIntelligence().summarize([Feedback("support", "good", 0.8)])
    assert result["average_sentiment"] == 0.8


def test_m93_feature_prioritization():
    ranked = FeaturePrioritizer().rank(
        [FeatureCandidate("a", 10, 1, 2), FeatureCandidate("b", 5, 1, 2)]
    )
    assert ranked[0].name == "a"


def test_m94_experiment_winner():
    exp = Experiment("checkout", "control", "treatment")
    assert ExperimentService().winner(
        exp, [VariantResult("control", 1), VariantResult("treatment", 2)]
    ) == "treatment"


def test_m95_improvement_plan():
    plan = ContinuousImprovement().plan("app", ["ship"], "feedback")
    assert plan.actions == ("ship",)
