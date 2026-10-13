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



def test_run_payloads_are_redacted_and_bounded_on_write(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "runs.db")
    token = "ghp_" + "A" * 30
    record = store.create(
        "run-safe",
        result={"message": f"failed with {token}", "nested": {"api_key": "secret-value"}},
        error=f"request failed token=super-secret-value {token}",
    )

    assert token not in str(record.result)
    assert record.result["nested"]["api_key"] == "[REDACTED]"
    assert "super-secret-value" not in (record.error or "")

    loaded = store.get("run-safe")
    assert loaded is not None
    assert token not in str(loaded.result)
    assert "super-secret-value" not in (loaded.error or "")


def test_legacy_database_payloads_are_sanitized_on_read(tmp_path: Path):
    import sqlite3

    database = tmp_path / "legacy-runs.db"
    store = PersistentRunStore(database)
    token = "ghp_" + "B" * 30
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO runtime_runs "
            "(run_id, status, result, error, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "legacy",
                "completed",
                '{"output": "' + token + '", "password": "old-secret"}',
                "old failure token=legacy-secret",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        connection.commit()

    loaded = store.get("legacy")
    assert loaded is not None
    assert token not in str(loaded.result)
    assert loaded.result["password"] == "[REDACTED]"
    assert "legacy-secret" not in (loaded.error or "")
    assert token not in str(store.list()[0].result)


def test_run_payload_depth_and_collection_sizes_are_bounded(tmp_path: Path):
    store = PersistentRunStore(tmp_path / "bounded-runs.db")
    nested = "end"
    for _ in range(12):
        nested = {"next": nested}
    record = store.create("deep", result={"items": list(range(300)), "nested": nested})

    assert len(record.result["items"]) == 200
    current = record.result["nested"]
    for _ in range(7):
        current = current["next"]
    assert current == "[TRUNCATED_MAX_DEPTH]"
