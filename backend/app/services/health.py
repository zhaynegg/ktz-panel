"""
Health index calculator — weighted 0–100 score with explainability.

Each parameter is scored individually (100 = perfect, 0 = critical) then
combined with configurable weights. The top contributing (worst) factors
are surfaced for the dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas import HealthFactor, HealthIndex


# (weight, ideal_value, warn_threshold, critical_threshold, higher_is_worse)
PARAMETER_CONFIG: dict[str, tuple[float, float, float, float, bool]] = {
    "engine_temp_c":           (0.20, 55.0, 85.0, 100.0, True),
    "transformer_temp_c":      (0.15, 50.0, 80.0, 95.0,  True),
    "brake_pipe_pressure_bar": (0.20, 5.0,  4.3,  3.5,   False),  # lower is worse
    "vibration_mm_s":          (0.15, 0.4,  1.8,  2.8,   True),
    "speed_kmh":               (0.05, 60.0, 80.0, 88.0,  True),
    "current_a":               (0.10, 300.0, 700.0, 900.0, True),
    "fuel_level_pct":          (0.10, 90.0, 20.0, 5.0,   False),  # lower is worse
    "voltage_v":               (0.05, 24750.0, 24200.0, 23900.0, False),
}


def _score_param(value: float, ideal: float, warn: float, crit: float, higher_is_worse: bool) -> float:
    """Map a single parameter to 0–100. 100 = at or better than ideal."""
    if higher_is_worse:
        if value <= ideal:
            return 100.0
        if value >= crit:
            return 0.0
        if value <= warn:
            return 100.0 - ((value - ideal) / (warn - ideal)) * 40.0  # 100 → 60
        return 60.0 - ((value - warn) / (crit - warn)) * 60.0         # 60 → 0
    else:
        if value >= ideal:
            return 100.0
        if value <= crit:
            return 0.0
        if value >= warn:
            return 100.0 - ((ideal - value) / (ideal - warn)) * 40.0
        return 60.0 - ((warn - value) / (warn - crit)) * 60.0


def compute_health(telemetry: dict[str, Any]) -> HealthIndex:
    """Compute health index from a single processed telemetry dict."""
    factors: list[HealthFactor] = []
    weighted_sum = 0.0
    total_weight = 0.0

    for param, (weight, ideal, warn, crit, higher_is_worse) in PARAMETER_CONFIG.items():
        val = telemetry.get(param)
        if val is None:
            continue

        score = _score_param(val, ideal, warn, crit, higher_is_worse)
        score = max(0.0, min(100.0, score))

        weighted_sum += score * weight
        total_weight += weight

        if score < 80:
            direction = "high" if higher_is_worse else "low"
            detail = f"{param}={val:.2f} — {'too ' + direction if score < 60 else 'elevated' if higher_is_worse else 'declining'}"
        else:
            detail = f"{param}={val:.2f} — normal"

        factors.append(HealthFactor(
            parameter=param,
            score=round(score, 1),
            weight=weight,
            detail=detail,
        ))

    index = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0

    if index >= 75:
        label = "GOOD"
    elif index >= 45:
        label = "WARNING"
    else:
        label = "CRITICAL"

    # Sort factors: worst first (lowest score) for explainability
    factors.sort(key=lambda f: f.score)

    return HealthIndex(
        value=index,
        label=label,
        factors=factors,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
