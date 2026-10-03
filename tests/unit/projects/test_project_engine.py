from src.projects.engine.project_engine import ProjectEngine
from src.projects.models.contracts import ProjectCreateRequest
from src.projects.models.enums import ProjectStatus


def make_project(engine: ProjectEngine):
    return engine.create(
        ProjectCreateRequest(
            name="Test Project",
            description="Project description",
            objective="Build a useful software product",
        )
    )


def test_create_project():
    engine = ProjectEngine()

    project = make_project(engine)

    assert project.name == "Test Project"
    assert project.status == ProjectStatus.IDEA
    assert project.id


def test_project_lifecycle_transition():
    engine = ProjectEngine()
    project = make_project(engine)

    engine.transition(project.id, ProjectStatus.RESEARCH)
    engine.transition(project.id, ProjectStatus.VALIDATION)
    engine.transition(project.id, ProjectStatus.PLANNING)

    assert engine.get(project.id).status == ProjectStatus.PLANNING


def test_invalid_project_transition():
    engine = ProjectEngine()
    project = make_project(engine)

    try:
        engine.transition(project.id, ProjectStatus.COMPLETED)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid transition to raise ValueError")


def test_project_filtering():
    engine = ProjectEngine()

    project = make_project(engine)
    engine.transition(project.id, ProjectStatus.RESEARCH)

    assert len(engine.list(ProjectStatus.RESEARCH)) == 1
    assert len(engine.list(ProjectStatus.IDEA)) == 0


def test_project_block():
    engine = ProjectEngine()
    project = make_project(engine)

    engine.transition(project.id, ProjectStatus.RESEARCH)
    engine.block(project.id)

    assert engine.get(project.id).status == ProjectStatus.BLOCKED
