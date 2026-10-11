from __future__ import annotations

from src.company.generated_task_planning import build_generated_task_plan
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission
from src.tasks.models.enums import TaskStatus


def test_generated_implementation_packages_gate_qa_in_real_task_scheduler() -> None:
    plan = build_generated_task_plan(
        "Expense Tracker",
        "Build an expense tracker with transactions, budgets, summaries, and tests.",
        {
            "index.html": "<main>Expense Tracker</main>",
            "app.js": "const transactions = [];",
            "src/api/transactions.py": "def list_transactions():\n    return []\n",
            "src/models/budget.py": "class Budget:\n    pass\n",
            "tests/test_expenses.py": (
                "def test_transaction_total():\n"
                "    assert sum([2, 3]) == 5\n"
            ),
        },
    )
    manager = MasterManager()
    manager.start_mission(
        Mission(
            name="Expense Tracker",
            objective="Build an expense tracker with transactions, budgets, summaries, and tests.",
            project_id="generated-expense-tracker",
        )
    )

    task_ids = manager.create_plan(plan)
    tasks = [manager.task_engine.get(task_id) for task_id in task_ids]
    implementation_count = len(plan) - 1

    assert implementation_count >= 2
    assert all(task.status == TaskStatus.READY for task in tasks[:implementation_count])
    assert tasks[-1].title.startswith("Validate ")
    assert tasks[-1].status == TaskStatus.BLOCKED
    assert set(tasks[-1].dependencies) == set(task_ids[:implementation_count])

    # Completing only part of the implementation must not release QA.
    manager.task_engine.start(task_ids[0])
    manager.task_engine.complete(task_ids[0])
    manager.task_engine.refresh_blocked_tasks()
    assert manager.task_engine.get(task_ids[-1]).status == TaskStatus.BLOCKED

    # Once every implementation package is complete, the scheduler releases QA.
    for task_id in task_ids[1:implementation_count]:
        manager.task_engine.start(task_id)
        manager.task_engine.complete(task_id)

    manager.task_engine.refresh_blocked_tasks()
    assert manager.task_engine.get(task_ids[-1]).status == TaskStatus.READY
