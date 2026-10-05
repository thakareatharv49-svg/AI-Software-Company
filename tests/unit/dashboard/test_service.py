from company.dashboard.service import CompanyDashboard


def test_dashboard_aggregates_company_state() -> None:
    dashboard = CompanyDashboard(
        {
            "company": lambda: {"name": "AI Software Company"},
            "projects": lambda: ({"id": "p1"},),
            "agents": lambda: ({"id": "a1"},),
            "tasks": lambda: ({"id": "t1"}, {"id": "t2"}),
            "research": lambda: ({"id": "r1"},),
            "failures": lambda: ({"id": "f1"},),
        }
    )

    snapshot = dashboard.snapshot()

    assert snapshot.company["name"] == "AI Software Company"
    assert len(snapshot.projects) == 1
    assert len(snapshot.agents) == 1
    assert len(snapshot.tasks) == 2
    assert len(snapshot.research) == 1
    assert dashboard.health()["failures"] == 1


def test_dashboard_is_safe_with_missing_providers() -> None:
    snapshot = CompanyDashboard().snapshot()

    assert snapshot.projects == ()
    assert snapshot.agents == ()
    assert snapshot.runtime == {}
    assert snapshot.audit == ()
