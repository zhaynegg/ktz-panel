"""
Simulator service — wraps LocomotiveSimulator from scripts/ and drives the
streaming loop. Also supports replay of historical data.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections import deque
from pathlib import Path
from typing import Any

# Make scripts/ importable
_SCRIPTS = Path(__file__).resolve().parents[2] / ".." / "scripts"
if str(_SCRIPTS.resolve()) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS.resolve()))

from locomotive_simulator import LocomotiveSimulator, run_scenario, simple_quality_check  # noqa: E402

from app.config import get_settings
from app.core.history_repository import HistoryRepository, get_history_repository
from app.schemas import QualityResult
from app.services.alerts import AlertEngine
from app.services.health_configurable import compute_health
from app.services.processing import TelemetryProcessor

logger = logging.getLogger(__name__)


class SimulatorService:
    """Manages the live simulator + processing pipeline."""

    def __init__(self, history_repository: HistoryRepository | None = None) -> None:
        settings = get_settings()
        self.sim = LocomotiveSimulator()
        self.sim.init(
            locomotive_type=settings.sim_locomotive_type,
            seed=settings.sim_seed,
        )
        self.sim.set_target_state("CRUISING")  # default start

        self.processor = TelemetryProcessor(
            alpha=settings.ema_alpha,
            buffer_size=settings.telemetry_buffer_size,
        )
        self.health_engine = compute_health  # stateless function
        self.alert_engine = AlertEngine()
        self.history_repository = history_repository or get_history_repository()

        self.tick_interval = settings.sim_tick_interval_s
        self._load_multiplier = 1
        self._running = False
        self._subscribers: list[asyncio.Queue] = []
        self._tick_count = 0
        self._frames: deque[dict[str, Any]] = deque(maxlen=settings.telemetry_buffer_size)

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Simulator streaming started (interval=%.2fs)", self.tick_interval)
        asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False

    async def _loop(self) -> None:
        while self._running:
            for _ in range(self._load_multiplier):
                frame = self.tick()
                for q in list(self._subscribers):
                    try:
                        q.put_nowait(frame)
                    except asyncio.QueueFull:
                        pass  # slow consumer, skip frame
            await asyncio.sleep(self.tick_interval)

    # ------------------------------------------------------------------
    # Single tick
    # ------------------------------------------------------------------

    def tick(self) -> dict[str, Any]:
        """Run one simulator step through the full pipeline."""
        raw = self.sim.update()
        processed = self.processor.process(raw)
        health = self.health_engine(processed)
        alerts = self.alert_engine.evaluate(processed)
        self._tick_count += 1

        frame = {
            "telemetry": processed,
            "health": health.model_dump(),
            "alerts": [a.model_dump() for a in alerts[:10]],
        }
        self._frames.append(frame)
        self.history_repository.append_frame(frame)
        return frame

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def set_state(self, state: str) -> None:
        self.sim.set_target_state(state.upper())

    def trigger_anomaly(self, name: str) -> None:
        self.sim.trigger_anomaly(name.upper())

    def refuel_full(self) -> None:
        self.sim.refuel_full()

    def set_load_multiplier(self, multiplier: int) -> None:
        self._load_multiplier = max(1, min(multiplier, 10))

    @property
    def load_multiplier(self) -> int:
        return self._load_multiplier

    def get_history(self, last_n: int | None = None) -> list[dict]:
        if last_n is None:
            return self.history_repository.fetch_recent_telemetry(self.tick_count or self.processor.buffer_size)
        return self.history_repository.fetch_recent_telemetry(last_n)

    def get_frame_history(self, last_n: int | None = None) -> list[dict[str, Any]]:
        if last_n is None:
            return self.history_repository.fetch_recent_frames(self.tick_count or self.processor.buffer_size)
        return self.history_repository.fetch_recent_frames(last_n)

    @property
    def tick_count(self) -> int:
        return self._tick_count

    # ------------------------------------------------------------------
    # Batch scenario (for graph endpoints)
    # ------------------------------------------------------------------

    @staticmethod
    def run_batch(
        ticks: int = 200,
        seed: int = 42,
        locomotive_type: str = "electric",
    ) -> tuple[list[dict], QualityResult]:
        """Run a full scenario, return (rows, quality_result)."""
        rows = run_scenario(ticks=ticks, seed=seed, locomotive_type=locomotive_type)
        q = simple_quality_check(rows)
        quality = QualityResult(
            passed=q["passed"],
            avg_residual=q["avg_residual"],
            max_residual=q["max_residual"],
            fault_ticks=q["fault_ticks"],
            total_ticks=q["total_ticks"],
            message=q["message"],
        )
        return rows, quality


# Global singleton
_service: SimulatorService | None = None


def get_simulator_service() -> SimulatorService:
    global _service
    if _service is None:
        _service = SimulatorService()
    return _service
