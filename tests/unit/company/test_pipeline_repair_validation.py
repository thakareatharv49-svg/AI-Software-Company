from pathlib import Path

import pytest

from src.company.execution.pipeline import CompanyExecutionPipeline
from src.company.project_generator import GeneratedProject, OllamaProjectGenerator
from src.qa.models.contracts import DebugDiagnosis, QATestRequest
from src.qa.models.enums import QATestStatus


class RepairGenerator:
    def __init__(self, repaired: GeneratedProject) -> None:
        self.repaired = repaired

    async def repair(self, files: dict[str, str], failure: str) -> GeneratedProject:
        return self.repaired

    _validate_mission_output = staticmethod(OllamaProjectGenerator._validate_mission_output)


@pytest.mark.asyncio
async def test_qa_repair_rejects_tautological_tests_before_writing_files(tmp_path: Path):
    pipeline = CompanyExecutionPipeline()
    original = {"main.py": "def total(values):\n    return sum(values)\n"}
    pipeline._active_generated_files = dict(original)
    pipeline.project_generator = RepairGenerator(
        GeneratedProject(
            files={
                "main.py": "def total(values):\n    return sum(values)\n",
                "tests/test_cli.py": "def test_total():\n    assert True\n",
            },
            test_command=["python", "-m", "pytest", "-q"],
        )
    )

    callback = pipeline._build_repair_callback(
        None,
        project_name="CLI Total Utility",
        objective="Build a Python CLI utility that sums numeric inputs.",
        project_id="repair-validation-test",
    )
    assert callback is not None

    accepted = await callback(
        QATestRequest(command=["python", "-m", "pytest", "-q"], working_directory=str(tmp_path)),
        DebugDiagnosis(
            attempt=1,
            test_status=QATestStatus.FAILED,
            error="The total calculation is incorrect.",
        ),
    )

    assert accepted is False
    assert pipeline._active_generated_files == original
    assert not (tmp_path / "tests" / "test_cli.py").exists()
    assert any(
        event.event_type == "qa.repair.rejected"
        for event in pipeline.event_service.list_events()
    )


@pytest.mark.asyncio
async def test_qa_repair_accepts_valid_mission_specific_tests(tmp_path: Path):
    pipeline = CompanyExecutionPipeline()
    repaired = GeneratedProject(
        files={
            "main.py": (
                "def total(values):\n"
                "    return sum(values)\n"
            ),
            "tests/test_cli.py": (
                "from main import total\n\n"
                "def test_total_sums_values():\n"
                "    assert total([2, 3, 5]) == 10\n\n"
                "def test_total_empty_input_is_zero():\n"
                "    assert total([]) == 0\n"
            ),
        },
        test_command=["python", "-m", "pytest", "-q"],
    )
    pipeline._active_generated_files = {"main.py": "def total(values): return 0\n"}
    pipeline.project_generator = RepairGenerator(repaired)

    callback = pipeline._build_repair_callback(
        None,
        project_name="CLI Total Utility",
        objective="Build a Python CLI utility that sums numeric inputs.",
        project_id="repair-validation-valid",
    )
    assert callback is not None

    accepted = await callback(
        QATestRequest(command=["python", "-m", "pytest", "-q"], working_directory=str(tmp_path)),
        DebugDiagnosis(
            attempt=1,
            test_status=QATestStatus.FAILED,
            error="The total calculation is incorrect.",
        ),
    )

    assert accepted is True
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == repaired.files["main.py"]
    assert (tmp_path / "tests" / "test_cli.py").is_file()
    assert pipeline._active_generated_files == repaired.files
