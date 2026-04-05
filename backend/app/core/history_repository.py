"""History repository contract and factory."""

from __future__ import annotations

from typing import Any, Protocol

from app.config import get_settings
from app.services.history_store import HistoryStore


Frame = dict[str, Any]


class HistoryRepository(Protocol):
    def append_frame(self, frame: Frame) -> None: ...
    def latest_frame(self) -> Frame | None: ...
    def fetch_recent_frames(self, last_n: int) -> list[Frame]: ...
    def fetch_recent_telemetry(self, last_n: int) -> list[Frame]: ...
    def fetch_frames_in_last_hours(self, hours: int) -> list[Frame]: ...
    def fetch_telemetry_in_last_hours(self, hours: int) -> list[Frame]: ...


_repository: HistoryRepository | None = None


def get_history_repository() -> HistoryRepository:
    global _repository
    if _repository is None:
        settings = get_settings()
        _repository = HistoryStore(
            db_path=settings.telemetry_history_db_path,
            retention_hours=settings.telemetry_history_retention_hours,
        )
    return _repository
