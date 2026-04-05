"""Russian-first AI analysis service for telemetry summaries and forecasts."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib import error, request

from app.config import get_settings
from app.core.ai_analysis import build_payload, fallback_response, insufficient_data_response, utc_now
from app.core.history import get_recent_frames
from app.schemas import AiMetricStats, AiSummaryResponse


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
                        "text": "Ты анализируешь телеметрию локомотива за последние 10 минут. Верни только JSON на русском языке. Не выдумывай факты, пиши кратко и осторожно.",
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
            return insufficient_data_response(settings.ai_analysis_window_minutes, enabled=False, source="disabled")

        frames = get_recent_frames(settings.ai_analysis_window_minutes * 60)
        if not frames:
            return insufficient_data_response(settings.ai_analysis_window_minutes)

        payload = build_payload(frames, settings.ai_analysis_window_minutes)
        cache_key = f"{payload['generated_at']}|{payload['current_health']}|{payload['active_alerts_count']}"
        if self._cache and time.time() < self._cache_until and self._cache_key == cache_key:
            return self._cache

        if not settings.openai_api_key:
            result = insufficient_data_response(settings.ai_analysis_window_minutes)
        else:
            try:
                ai_result = _call_openai(payload, settings.openai_api_key, settings.openai_model)
                result = AiSummaryResponse(
                    enabled=True,
                    available=True,
                    source="openai",
                    model=settings.openai_model,
                    generated_at=str(payload.get("generated_at", utc_now())),
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
            except error.HTTPError as exc:
                if exc.code == 429:
                    result = fallback_response(
                        payload,
                        "AI-вызов временно недоступен из-за лимита API. Используется локальный резервный анализ.",
                    )
                else:
                    result = fallback_response(
                        payload,
                        "AI-вызов временно недоступен. Используется локальный резервный анализ.",
                    )
            except (ValueError, KeyError, error.URLError, TimeoutError, json.JSONDecodeError):
                result = fallback_response(
                    payload,
                    "AI-вызов временно недоступен. Используется локальный резервный анализ.",
                )

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
