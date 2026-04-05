"""
Health index calculator with JSON-configurable weights and thresholds.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.config import get_settings
from app.schemas import HealthConfig, HealthFactor, HealthIndex

logger = logging.getLogger(__name__)

DEFAULT_HEALTH_CONFIG = HealthConfig.model_validate(
    {
        "thresholds": {
            "good_min": 75.0,
            "warning_min": 45.0,
        },
        "parameters": {
            "engine_temp_c": {"weight": 0.20, "ideal": 55.0, "warn": 85.0, "crit": 100.0, "higher_is_worse": True},
            "transformer_temp_c": {"weight": 0.15, "ideal": 50.0, "warn": 80.0, "crit": 95.0, "higher_is_worse": True},
            "brake_pipe_pressure_bar": {"weight": 0.20, "ideal": 5.0, "warn": 4.3, "crit": 3.5, "higher_is_worse": False},
            "vibration_mm_s": {"weight": 0.15, "ideal": 0.4, "warn": 1.8, "crit": 2.8, "higher_is_worse": True},
            "speed_kmh": {"weight": 0.05, "ideal": 60.0, "warn": 80.0, "crit": 88.0, "higher_is_worse": True},
            "current_a": {"weight": 0.10, "ideal": 300.0, "warn": 700.0, "crit": 900.0, "higher_is_worse": True},
            "fuel_level_pct": {"weight": 0.10, "ideal": 90.0, "warn": 20.0, "crit": 5.0, "higher_is_worse": False},
            "voltage_v": {"weight": 0.05, "ideal": 24750.0, "warn": 24200.0, "crit": 23900.0, "higher_is_worse": False},
        },
    }
)

_cached_config: HealthConfig | None = None
_cached_mtime: float | None = None
_cached_path: str | None = None


def _score_param(value: float, ideal: float, warn: float, crit: float, higher_is_worse: bool) -> float:
    if higher_is_worse:
        if value <= ideal:
            return 100.0
        if value >= crit:
            return 0.0
        if value <= warn:
            return 100.0 - ((value - ideal) / (warn - ideal)) * 40.0
        return 60.0 - ((value - warn) / (crit - warn)) * 60.0

    if value >= ideal:
        return 100.0
    if value <= crit:
        return 0.0
    if value >= warn:
        return 100.0 - ((ideal - value) / (ideal - warn)) * 40.0
    return 60.0 - ((warn - value) / (warn - crit)) * 60.0


def get_health_config() -> HealthConfig:
    global _cached_config, _cached_mtime, _cached_path

    settings = get_settings()
    config_path = Path(settings.health_config_path)

    try:
        mtime = config_path.stat().st_mtime
    except OSError:
        mtime = None

    if _cached_config is not None and _cached_path == str(config_path) and _cached_mtime == mtime:
        return _cached_config

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        loaded = HealthConfig.model_validate(raw)
        _cached_config = loaded
        _cached_mtime = mtime
        _cached_path = str(config_path)
        return loaded
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Falling back to default health config: %s", exc)
        _cached_config = DEFAULT_HEALTH_CONFIG
        _cached_mtime = mtime
        _cached_path = str(config_path)
        return DEFAULT_HEALTH_CONFIG


def compute_health(telemetry: dict[str, Any]) -> HealthIndex:
    config = get_health_config()
    factors: list[HealthFactor] = []
    weighted_sum = 0.0
    total_weight = 0.0

    for param, rules in config.parameters.items():
        val = telemetry.get(param)
        if val is None:
            continue

        numeric_value = float(val)
        score = _score_param(
            numeric_value,
            rules.ideal,
            rules.warn,
            rules.crit,
            rules.higher_is_worse,
        )
        score = max(0.0, min(100.0, score))

        weighted_sum += score * rules.weight
        total_weight += rules.weight

        if score < 80:
            direction = "high" if rules.higher_is_worse else "low"
            detail = f"{param}={numeric_value:.2f} - {'too ' + direction if score < 60 else 'elevated' if rules.higher_is_worse else 'declining'}"
        else:
            detail = f"{param}={numeric_value:.2f} - normal"

        factors.append(
            HealthFactor(
                parameter=param,
                score=round(score, 1),
                weight=rules.weight,
                detail=detail,
            )
        )

    index = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0

    if index >= config.thresholds.good_min:
        label = "GOOD"
    elif index >= config.thresholds.warning_min:
        label = "WARNING"
    else:
        label = "CRITICAL"

    factors.sort(key=lambda factor: factor.score)

    return HealthIndex(
        value=index,
        label=label,
        factors=factors,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
