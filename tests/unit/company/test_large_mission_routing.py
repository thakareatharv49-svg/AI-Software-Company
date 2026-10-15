import pytest

from src.company.project_generator import OllamaProjectGenerator


@pytest.mark.parametrize(
    ("name", "objective"),
    [
        ("Clinic Management System", "Build a clinic management system"),
        ("Marketplace", "Create a marketplace for local sellers"),
        ("Inventory Dashboard", "Build an inventory dashboard"),
        ("Project Management Platform", "Create a project management platform"),
        ("Learning Management System", "Build a learning management system"),
        ("Booking Platform", "Create a booking platform"),
        ("Analytics Dashboard", "Build an analytics dashboard"),
        ("Inventory Management System", "Build an inventory management system"),
    ],
)
def test_complex_product_categories_use_modular_generation(name, objective):
    assert OllamaProjectGenerator._is_large_mission(name, objective)


@pytest.mark.parametrize(
    ("name", "objective"),
    [
        ("Simple Greeting Script", "Print a greeting from a Python script"),
        ("Calculator", "Build a calculator"),
    ],
)
def test_small_missions_keep_the_single_pass_path(name, objective):
    assert not OllamaProjectGenerator._is_large_mission(name, objective)


@pytest.mark.parametrize(
    ("name", "objective"),
    [
        ("Shadow Arena", "Build a 2D fighting game"),
        ("Pocket Planner", "Build a native Android app"),
        ("Appointment API", "Create a REST API for appointments"),
        ("Data Pipeline", "Build an ETL pipeline"),
        ("Reusable SDK", "Create a Python library and SDK"),
        ("Desktop Studio", "Build a Windows desktop app"),
    ],
)
def test_short_non_browser_products_use_resumable_generation(name, objective):
    assert OllamaProjectGenerator._is_large_mission(name, objective)

@pytest.mark.parametrize(
    "objective",
    [
        "Build a capital gains tax calculator with charts",
        "Create a rapid personal finance dashboard",
    ],
)
def test_unrelated_words_do_not_trigger_backend_requirement(objective):
    assert not OllamaProjectGenerator._mission_requires_backend(objective)


@pytest.mark.parametrize(
    "objective",
    [
        "Build a web app with a REST API",
        "Create an API endpoint for expense records",
        "Build an API-only service for appointment management",
        "Build a database-backed inventory app",
    ],
)
def test_explicit_server_capabilities_require_backend(objective):
    assert OllamaProjectGenerator._mission_requires_backend(objective)


def test_explicit_frontend_only_exclusion_overrides_backend_terms():
    assert not OllamaProjectGenerator._mission_requires_backend(
        "Build a frontend-only expense tracker without a backend or API"
    )



def test_appointment_api_is_not_misclassified_as_a_browser_app():
    assert not OllamaProjectGenerator._is_browser_mission(
        "Appointment Service API: Build a REST API for managing appointments"
    )
    assert OllamaProjectGenerator._is_browser_mission(
        "Notes App: create and search notes in a browser"
    )
