"""Shared helpers for AI telemetry analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from app.schemas import AiMetricStats, AiSummaryResponse

METRIC_KEYS = [
    "speed_kmh",
    "current_a",
    "engine_temp_c",
    "transformer_temp_c",
    "brake_pipe_pressure_bar",
    "vibration_mm_s",
    "fuel_level_pct",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def risk_from_health(current_health: float, health_delta: float, active_alerts_count: int) -> str:
    if current_health < 45 or active_alerts_count > 0:
        return "high"
    if current_health < 75 or health_delta <= -5:
        return "medium"
    return "low"


def compute_trend(values: list[float], improving_when_down: bool = False) -> str:
    if len(values) < 5:
        return "stable"

    segment = max(1, len(values) // 5)
    start = mean(values[:segment])
    end = mean(values[-segment:])
    delta = end - start
    tolerance = max(abs(start) * 0.03, 0.15)

    if abs(delta) <= tolerance:
        return "stable"
    if improving_when_down:
        return "recovering" if delta < 0 else "rising"
    return "rising" if delta > 0 else "falling"


def build_metric_stats(frames: list[dict[str, Any]]) -> dict[str, AiMetricStats]:
    metrics: dict[str, AiMetricStats] = {}
    for key in METRIC_KEYS:
        values = [
            float(frame["telemetry"].get(key))
            for frame in frames
            if frame.get("telemetry") and frame["telemetry"].get(key) is not None
        ]
        if not values:
            continue

        improving_when_down = key in {"vibration_mm_s", "engine_temp_c", "transformer_temp_c", "current_a"}
        metrics[key] = AiMetricStats(
            min=round(min(values), 2),
            max=round(max(values), 2),
            avg=round(mean(values), 2),
            trend=compute_trend(values, improving_when_down=improving_when_down),
        )
    return metrics


def build_event_list(frames: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen_ids: set[str] = set()
    events: list[dict[str, str]] = []
    for frame in frames:
        for alert in frame.get("alerts", []):
            alert_id = str(alert.get("id", ""))
            if not alert_id or alert_id in seen_ids:
                continue
            seen_ids.add(alert_id)
            events.append(
                {
                    "ts": str(alert.get("ts", "")),
                    "severity": str(alert.get("severity", "info")),
                    "title": str(alert.get("title", "Alert")),
                }
            )
    return events[-10:]


def build_payload(frames: list[dict[str, Any]], window_minutes: int) -> dict[str, Any]:
    latest = frames[-1]
    earliest = frames[0]
    current_health = float(latest["health"]["value"])
    previous_health = float(earliest["health"]["value"])
    health_delta = round(current_health - previous_health, 1)
    top_factors = latest["health"].get("factors", [])[:5]
    active_alerts = latest.get("alerts", [])

    return {
        "window_minutes": window_minutes,
        "generated_at": latest["telemetry"].get("timestamp", utc_now()),
        "current_health": current_health,
        "previous_health": previous_health,
        "health_delta": health_delta,
        "current_state": latest["telemetry"].get("state", "UNKNOWN"),
        "active_alerts_count": len(active_alerts),
        "active_alerts": [
            {
                "severity": alert.get("severity", "info"),
                "title": alert.get("title", "Alert"),
                "detail": alert.get("detail"),
                "recommendation": alert.get("recommendation"),
            }
            for alert in active_alerts[:6]
        ],
        "recent_events": build_event_list(frames),
        "top_factors": [
            {
                "parameter": factor.get("parameter", "unknown"),
                "score": factor.get("score", 0),
                "weight": factor.get("weight", 0),
                "detail": factor.get("detail", ""),
            }
            for factor in top_factors
        ],
        "metrics": {key: stats.model_dump() for key, stats in build_metric_stats(frames).items()},
    }


def fallback_response(payload: dict[str, Any], reason: str, source: str = "fallback") -> AiSummaryResponse:
    current_health = float(payload.get("current_health", 0.0))
    health_delta = float(payload.get("health_delta", 0.0))
    active_alerts_count = int(payload.get("active_alerts_count", 0))
    current_state = str(payload.get("current_state", "UNKNOWN"))
    top_factors = payload.get("top_factors", [])
    weakest = top_factors[0]["parameter"] if top_factors else "system load"
    metrics = {key: AiMetricStats.model_validate(value) for key, value in payload.get("metrics", {}).items()}

    if active_alerts_count > 0:
        summary = f"За последние {payload['window_minutes']} минут система фиксирует активные алерты и повышенный риск."
        forecast = "Если текущие сигналы сохранятся, возможен переход к более тяжёлому сценарию в ближайшие 5-10 минут."
        recommendations = [
            "Проверить активные алерты и их рекомендации.",
            "Снизить нагрузку на локомотив до стабилизации параметров.",
            "Продолжить мониторинг ключевых факторов риска.",
        ]
    else:
        summary = f"За последние {payload['window_minutes']} минут система работала в состоянии {current_state}, индекс здоровья {current_health:.1f}."
        forecast = "При сохранении текущего тренда резкого ухудшения в ближайшие 5-10 минут не ожидается."
        recommendations = [
            f"Продолжить наблюдение за фактором {weakest}.",
            "Сверять AI-оценку с трендами и alert-лентой.",
            "Использовать replay и summary export для фиксации отклонений.",
        ]

    return AiSummaryResponse(
        enabled=True,
        available=False,
        source=source,
        model=None,
        generated_at=str(payload.get("generated_at", utc_now())),
        window_minutes=int(payload.get("window_minutes", 10)),
        risk_level=risk_from_health(current_health, health_delta, active_alerts_count),
        summary=f"{summary} {reason}",
        forecast=forecast,
        recommendations=recommendations,
        current_health=current_health,
        previous_health=float(payload.get("previous_health", current_health)),
        health_delta=health_delta,
        active_alerts_count=active_alerts_count,
        metrics=metrics,
    )


def insufficient_data_response(window_minutes: int, enabled: bool = True, source: str = "unavailable") -> AiSummaryResponse:
    return AiSummaryResponse(
        enabled=enabled,
        available=False,
        source=source,
        model=None,
        generated_at=utc_now(),
        window_minutes=window_minutes,
        risk_level="low",
        summary=f"Недостаточно данных для AI-анализа: история ещё не накопилась. Нужно {window_minutes} минут.",
        forecast="Дождитесь накопления окна последних минут.",
        recommendations=["Подождать 2-3 минуты.", "Проверить live stream.", "Повторить запрос позже."],
        current_health=0.0,
        previous_health=0.0,
        health_delta=0.0,
        active_alerts_count=0,
        metrics={},
    )
