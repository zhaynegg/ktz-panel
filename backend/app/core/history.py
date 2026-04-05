"""Helpers for reading recent simulator history and snapshots."""

from __future__ import annotations

from typing import Any

from app.services.simulator import get_simulator_service


Frame = dict[str, Any]


def get_recent_frames(last_n: int) -> list[Frame]:
    service = get_simulator_service()
    return service.get_frame_history(last_n=max(1, last_n))


def get_processed_rows(last_n: int) -> list[Frame]:
    service = get_simulator_service()
    return service.get_history(last_n=max(1, last_n))


def get_recent_frames_by_hours(hours: int) -> list[Frame]:
    service = get_simulator_service()
    return service.history_repository.fetch_frames_in_last_hours(hours)


def get_processed_rows_by_hours(hours: int) -> list[Frame]:
    service = get_simulator_service()
    return service.history_repository.fetch_telemetry_in_last_hours(hours)


def get_current_snapshot() -> Frame:
    service = get_simulator_service()
    latest = service.history_repository.latest_frame()
    if latest:
        return latest
    frames = service.get_frame_history(last_n=1)
    if frames:
        return frames[-1]
    return service.tick()
