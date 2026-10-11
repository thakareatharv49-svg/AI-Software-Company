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
