from src.company.project_factory import FactoryProject, ProjectFactory


def test_factory_retries_are_appended_after_waiting_missions():
    factory = object.__new__(ProjectFactory)
    first = object()
    waiting = object()
    factory.queue = [waiting]
    factory.queue.append(first)
    assert factory.queue == [waiting, first]
