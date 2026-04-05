"""AI analysis service for telemetry summaries and short forecasts."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from statistics import mean
from typing import Any
from urllib import error, request

from app.config import get_settings
from app.schemas import AiMetricStats, AiSummaryResponse
from app.services.simulator import get_simulator_service

METRIC_KEYS = [
    "speed_kmh",
    "current_a",
    "engine_temp_c",
    "transformer_temp_c",
    "brake_pipe_pressure_bar",
    "vibration_mm_s",
    "fuel_level_pct",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_from_health(current_health: float, health_delta: float, active_alerts_count: int) -> str:
    if current_health < 45 or active_alerts_count > 0:
        return "high"
    if current_health < 75 or health_delta <= -5:
        return "medium"
    return "low"


def _compute_trend(values: list[float], improving_when_down: bool = False) -> str:
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


def _build_metric_stats(frames: list[dict[str, Any]]) -> dict[str, AiMetricStats]:
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
            trend=_compute_trend(values, improving_when_down=improving_when_down),
        )
    return metrics


def _event_list(frames: list[dict[str, Any]]) -> list[dict[str, str]]:
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


def _build_payload(frames: list[dict[str, Any]], window_minutes: int) -> dict[str, Any]:
    latest = frames[-1]
    earliest = frames[0]
    current_health = float(latest["health"]["value"])
    previous_health = float(earliest["health"]["value"])
    health_delta = round(current_health - previous_health, 1)
    top_factors = latest["health"].get("factors", [])[:5]
    active_alerts = latest.get("alerts", [])

    return {
        "window_minutes": window_minutes,
        "generated_at": latest["telemetry"].get("timestamp", _utc_now()),
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
        "recent_events": _event_list(frames),
        "top_factors": [
            {
                "parameter": factor.get("parameter", "unknown"),
                "score": factor.get("score", 0),
                "weight": factor.get("weight", 0),
                "detail": factor.get("detail", ""),
            }
            for factor in top_factors
        ],
        "metrics": {key: stats.model_dump() for key, stats in _build_metric_stats(frames).items()},
    }


def _fallback_response(payload: dict[str, Any], reason: str, source: str = "fallback") -> AiSummaryResponse:
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
        generated_at=str(payload.get("generated_at", _utc_now())),
        window_minutes=int(payload.get("window_minutes", 10)),
        risk_level=_risk_from_health(current_health, health_delta, active_alerts_count),
        summary=f"{summary} {reason}",
        forecast=forecast,
        recommendations=recommendations,
        current_health=current_health,
        previous_health=float(payload.get("previous_health", current_health)),
        health_delta=health_delta,
        active_alerts_count=active_alerts_count,
        metrics=metrics,
    )


def _extract_text(response_json: dict[str, Any]) -> str:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in response_json.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise ValueError("No output text returned by OpenAI")


def _call_openai(payload: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "summary": {"type": "string"},
            "forecast": {"type": "string"},
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
        },
        "required": ["risk_level", "summary", "forecast", "recommendations"],
    }

    request_body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You analyze locomotive telemetry for the last 10 minutes. Return only JSON, be cautious, and do not invent facts.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=True)}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "locomotive_ai_summary",
                "schema": schema,
                "strict": True,
            }
        },
    }

    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return json.loads(_extract_text(data))


class AiAnalysisService:
    def __init__(self) -> None:
        self._cache: AiSummaryResponse | None = None
        self._cache_until = 0.0
        self._cache_key = ""

    def summarize_last_window(self) -> AiSummaryResponse:
        settings = get_settings()
        if not settings.ai_analysis_enabled:
            return AiSummaryResponse(
                enabled=False,
                available=False,
                source="disabled",
                model=None,
                generated_at=_utc_now(),
                window_minutes=settings.ai_analysis_window_minutes,
                risk_level="low",
                summary="AI analysis is disabled in configuration.",
                forecast="Enable AI analysis and set OPENAI_API_KEY to receive forecasts.",
                recommendations=["Set AI_ANALYSIS_ENABLED=true.", "Add OPENAI_API_KEY.", "Restart backend."],
                current_health=0.0,
                previous_health=0.0,
                health_delta=0.0,
                active_alerts_count=0,
                metrics={},
            )

        service = get_simulator_service()
        frames = service.get_frame_history(last_n=max(1, settings.ai_analysis_window_minutes * 60))
        if not frames:
            return AiSummaryResponse(
                enabled=True,
                available=False,
                source="unavailable",
                model=None,
                generated_at=_utc_now(),
                window_minutes=settings.ai_analysis_window_minutes,
                risk_level="low",
                summary="Недостаточно данных для AI-анализа: история ещё не накопилась.",
                forecast="Дождитесь накопления окна последних минут.",
                recommendations=["Подождать 2-3 минуты.", "Проверить live stream.", "Повторить запрос позже."],
                current_health=0.0,
                previous_health=0.0,
                health_delta=0.0,
                active_alerts_count=0,
                metrics={},
            )

        payload = _build_payload(frames, settings.ai_analysis_window_minutes)
        cache_key = f"{payload['generated_at']}|{payload['current_health']}|{payload['active_alerts_count']}"
        if self._cache and time.time() < self._cache_until and self._cache_key == cache_key:
            return self._cache

        if not settings.openai_api_key:
            result = _fallback_response(payload, "OpenAI API key is not configured.", source="fallback")
        else:
            try:
                ai_result = _call_openai(payload, settings.openai_api_key, settings.openai_model)
                result = AiSummaryResponse(
                    enabled=True,
                    available=True,
                    source="openai",
                    model=settings.openai_model,
                    generated_at=str(payload["generated_at"]),
                    window_minutes=int(payload["window_minutes"]),
                    risk_level=str(ai_result["risk_level"]),
                    summary=str(ai_result["summary"]),
                    forecast=str(ai_result["forecast"]),
                    recommendations=[str(item) for item in ai_result["recommendations"]],
                    current_health=float(payload["current_health"]),
                    previous_health=float(payload["previous_health"]),
                    health_delta=float(payload["health_delta"]),
                    active_alerts_count=int(payload["active_alerts_count"]),
                    metrics={key: AiMetricStats.model_validate(value) for key, value in payload["metrics"].items()},
                )
            except (ValueError, KeyError, error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
                result = _fallback_response(payload, f"AI backend fallback engaged: {exc}", source="fallback")

        self._cache = result
        self._cache_key = cache_key
        self._cache_until = time.time() + max(5, settings.ai_analysis_cache_seconds)
        return result


_service: AiAnalysisService | None = None


def get_ai_analysis_service() -> AiAnalysisService:
    global _service
    if _service is None:
        _service = AiAnalysisService()
    return _service
