from pathlib import Path

import pytest

from src.company.runtime.persistent_run_store import PersistentRunStore


def test_create_and_get(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")

    created = store.create("run-1")

    assert created.run_id == "run-1"
    assert created.status == "submitted"

    loaded = store.get("run-1")

    assert loaded is not None
    assert loaded.run_id == "run-1"
    assert loaded.status == "submitted"


def test_update(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")
    store.create("run-1")

    updated = store.update(
        "run-1",
        status="completed",
        result={"success": True},
    )

    assert updated.status == "completed"
    assert updated.result == {"success": True}


def test_persistence_across_instances(tmp_path: Path):
    database = tmp_path / "runs.db"

    PersistentRunStore(database).create(
        "run-1",
        status="completed",
        result={"value": 42},
    )

    second_store = PersistentRunStore(database)
    loaded = second_store.get("run-1")

    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.result == {"value": 42}


def test_missing_run(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")

    assert store.get("missing") is None


def test_update_missing_run(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")

    with pytest.raises(KeyError):
        store.update("missing", status="failed")


def test_list_runs(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")

    store.create("run-1")
    store.create("run-2", status="completed")

    runs = store.list()

    assert {run.run_id for run in runs} == {"run-1", "run-2"}


def test_delete_run(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")

    store.create("run-1")
    store.delete("run-1")

    assert store.get("run-1") is None
