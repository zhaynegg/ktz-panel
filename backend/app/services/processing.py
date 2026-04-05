"""Telemetry processing: EMA smoothing, validation, and ring buffer."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Reasonable physical bounds for validation
BOUNDS = {
    "speed_kmh":               (0.0, 120.0),
    "traction_power_kw":       (0.0, 7000.0),
    "engine_temp_c":           (20.0, 150.0),
    "transformer_temp_c":      (20.0, 150.0),
    "brake_pipe_pressure_bar": (1.0, 7.0),
    "voltage_v":               (20000.0, 30000.0),
    "current_a":               (0.0, 1200.0),
    "vibration_mm_s":          (0.0, 10.0),
    "fuel_level_pct":          (0.0, 100.0),
}

NUMERIC_FIELDS = list(BOUNDS.keys())


@dataclass
class TelemetryProcessor:
    """EMA smoothing + validation + ring-buffer for the last N ticks."""

    alpha: float = 0.3
    buffer_size: int = 600
    buffer: deque = field(default_factory=deque)
    _ema: dict[str, float] = field(default_factory=dict)

    def process(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate → smooth → buffer. Returns processed dict."""
        validated = self._validate(raw)
        smoothed = self._ema_smooth(validated)

        # Attach raw values for key fields (useful for charts)
        smoothed["raw_speed_kmh"] = validated.get("speed_kmh", 0.0)
        smoothed["raw_engine_temp_c"] = validated.get("engine_temp_c", 0.0)

        self.buffer.append(smoothed)
        if len(self.buffer) > self.buffer_size:
            self.buffer.popleft()

        return smoothed

    def get_history(self, last_n: int | None = None) -> list[dict]:
        """Return buffered ticks (most recent last)."""
        if last_n is None:
            return list(self.buffer)
        return list(self.buffer)[-last_n:]

    # ------------------------------------------------------------------

    def _validate(self, raw: dict[str, Any]) -> dict[str, Any]:
        out = dict(raw)
        for key, (lo, hi) in BOUNDS.items():
            val = raw.get(key)
            if val is None:
                continue
            if not isinstance(val, (int, float)):
                logger.warning("Non-numeric %s=%r — clamping", key, val)
                out[key] = lo
                continue
            if val < lo or val > hi:
                logger.debug("Clamping %s=%.2f to [%.1f, %.1f]", key, val, lo, hi)
                out[key] = max(lo, min(hi, val))
        return out

    def _ema_smooth(self, validated: dict[str, Any]) -> dict[str, Any]:
        out = dict(validated)
        a = self.alpha
        for key in NUMERIC_FIELDS:
            val = validated.get(key)
            if val is None:
                continue
            prev = self._ema.get(key)
            if prev is None:
                self._ema[key] = val
            else:
                smoothed = a * val + (1 - a) * prev
                self._ema[key] = smoothed
                out[key] = round(smoothed, 4)
        return out
