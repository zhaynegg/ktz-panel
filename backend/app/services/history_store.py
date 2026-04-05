"""Persistent short-term telemetry history backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class HistoryStore:
    """Stores processed frames for 24-72h style replay and export windows."""

    def __init__(self, db_path: str, retention_hours: int = 72) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_hours = retention_hours
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    frame_json TEXT NOT NULL,
                    telemetry_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_history_ts ON telemetry_history(ts DESC)"
            )
            conn.commit()

    def append_frame(self, frame: dict[str, Any]) -> None:
        telemetry = frame.get("telemetry", {})
        timestamp = str(telemetry.get("timestamp", datetime.now(timezone.utc).isoformat()))
        frame_json = json.dumps(frame, ensure_ascii=False)
        telemetry_json = json.dumps(telemetry, ensure_ascii=False)

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO telemetry_history (ts, frame_json, telemetry_json)
                VALUES (?, ?, ?)
                """,
                (timestamp, frame_json, telemetry_json),
            )
            self._prune_locked(conn)
            conn.commit()

    def latest_frame(self) -> dict[str, Any] | None:
        rows = self.fetch_recent_frames(1)
        return rows[-1] if rows else None

    def fetch_recent_frames(self, last_n: int) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT frame_json
                FROM telemetry_history
                ORDER BY ts DESC, id DESC
                LIMIT ?
                """,
                (max(1, last_n),),
            ).fetchall()
        return [json.loads(row["frame_json"]) for row in reversed(rows)]

    def fetch_recent_telemetry(self, last_n: int) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT telemetry_json
                FROM telemetry_history
                ORDER BY ts DESC, id DESC
                LIMIT ?
                """,
                (max(1, last_n),),
            ).fetchall()
        return [json.loads(row["telemetry_json"]) for row in reversed(rows)]

    def fetch_frames_in_last_hours(self, hours: int) -> list[dict[str, Any]]:
        cutoff = self._cutoff_iso(hours)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT frame_json
                FROM telemetry_history
                WHERE ts >= ?
                ORDER BY ts ASC, id ASC
                """,
                (cutoff,),
            ).fetchall()
        return [json.loads(row["frame_json"]) for row in rows]

    def fetch_telemetry_in_last_hours(self, hours: int) -> list[dict[str, Any]]:
        cutoff = self._cutoff_iso(hours)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT telemetry_json
                FROM telemetry_history
                WHERE ts >= ?
                ORDER BY ts ASC, id ASC
                """,
                (cutoff,),
            ).fetchall()
        return [json.loads(row["telemetry_json"]) for row in rows]

    def _prune_locked(self, conn: sqlite3.Connection) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        conn.execute("DELETE FROM telemetry_history WHERE ts < ?", (cutoff.isoformat(),))

    @staticmethod
    def _cutoff_iso(hours: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(hours=max(1, hours))).isoformat()
