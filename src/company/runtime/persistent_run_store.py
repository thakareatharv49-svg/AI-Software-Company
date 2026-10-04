from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class PersistentRunRecord:
    run_id: str
    status: str
    result: Any = None
    error: str | None = None
    created_at: str = ""
    updated_at: str = ""


class PersistentRunStore:
    def __init__(self, database_path: str | Path = "runtime_runs.db") -> None:
        self.database_path = str(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _encode(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str)

    @staticmethod
    def _decode(value: str | None) -> Any:
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def create(
        self,
        run_id: str,
        *,
        status: str = "submitted",
        result: Any = None,
        error: str | None = None,
    ) -> PersistentRunRecord:
        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runtime_runs
                (run_id, status, result, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    status,
                    self._encode(result),
                    error,
                    now,
                    now,
                ),
            )
            connection.commit()

        return PersistentRunRecord(
            run_id=run_id,
            status=status,
            result=result,
            error=error,
            created_at=now,
            updated_at=now,
        )

    def get(self, run_id: str) -> PersistentRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, status, result, error, created_at, updated_at
                FROM runtime_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        return PersistentRunRecord(
            run_id=row["run_id"],
            status=row["status"],
            result=self._decode(row["result"]),
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update(
        self,
        run_id: str,
        *,
        status: str | None = None,
        result: Any = None,
        error: str | None = None,
    ) -> PersistentRunRecord:
        current = self.get(run_id)

        if current is None:
            raise KeyError(run_id)

        new_status = status if status is not None else current.status
        new_result = result if result is not None else current.result
        new_error = error if error is not None else current.error
        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_runs
                SET status = ?, result = ?, error = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (
                    new_status,
                    self._encode(new_result),
                    new_error,
                    now,
                    run_id,
                ),
            )
            connection.commit()

        return PersistentRunRecord(
            run_id=run_id,
            status=new_status,
            result=new_result,
            error=new_error,
            created_at=current.created_at,
            updated_at=now,
        )

    def delete(self, run_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM runtime_runs WHERE run_id = ?",
                (run_id,),
            )
            connection.commit()

    def list(self) -> list[PersistentRunRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, status, result, error, created_at, updated_at
                FROM runtime_runs
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [
            PersistentRunRecord(
                run_id=row["run_id"],
                status=row["status"],
                result=self._decode(row["result"]),
                error=row["error"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
