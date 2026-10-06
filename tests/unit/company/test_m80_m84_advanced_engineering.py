from company.engineering import (
    CodingAgent, DebuggingService, Dependency, DependencyManager,
    RefactoringService, RepositoryIntelligence,
)

def test_m80_coding_agent_plan_and_execution():
    agent = CodingAgent()
    plan = agent.plan("add feature")
    assert plan.steps == ("inspect", "implement", "test", "review")
    assert len(agent.execute(plan, lambda step: step)) == 4

def test_m81_repository_intelligence_indexes_files_and_symbols():
    index = RepositoryIntelligence().index({"app.py": "class App:\n    def run(self):\n        pass"})
    assert index.languages == ("py",)
    assert "class App" in index.symbols

def test_m82_debugging_is_bounded():
    calls = 0
    def operation():
        nonlocal calls
        calls += 1
        raise RuntimeError("broken")
    attempts = DebuggingService(2).run(operation)
    assert len(attempts) == 2
    assert calls == 2
    assert not attempts[-1].success

def test_m83_refactoring_is_reviewable():
    plan = RefactoringService().plan("module.py")
    assert "review diff" in plan.steps

def test_m84_dependency_management_detects_updates():
    manager = DependencyManager()
    item = Dependency("fastapi", "1.0", latest="2.0")
    assert manager.outdated([item]) == (item,)
    assert manager.plan(item) == "upgrade fastapi from 1.0 to 2.0"
