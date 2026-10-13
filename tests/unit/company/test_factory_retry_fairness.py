from types import SimpleNamespace

from src.company.project_factory import ProjectFactory


def test_retry_is_appended_after_waiting_missions_without_duplicates():
    factory = object.__new__(ProjectFactory)
    waiting = SimpleNamespace(mission=SimpleNamespace(id="waiting"))
    retrying = SimpleNamespace(mission=SimpleNamespace(id="retrying"))
    factory.queue = [waiting]

    factory._requeue_for_fairness(retrying)
    factory._requeue_for_fairness(retrying)

    assert factory.queue == [waiting, retrying]
