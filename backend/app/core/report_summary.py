"""PDF summary text composition helpers."""

from __future__ import annotations

from typing import Any

from app.schemas import AiSummaryResponse

RECOMMENDATION_TRANSLATIONS = {
    "Reduce throttle immediately; inspect cooling system": "Немедленно снизить тягу и проверить систему охлаждения.",
    "Emergency stop procedure; check brake line integrity": "Выполнить процедуру аварийной остановки и проверить целостность тормозной магистрали.",
    "Reduce speed; inspect bogies and track condition": "Снизить скорость и проверить тележки и состояние пути.",
    "Reduce traction demand; check for short circuits": "Снизить тяговую нагрузку и проверить систему на короткие замыкания.",
    "Monitor closely; consider reducing load": "Вести усиленный мониторинг и при необходимости снизить нагрузку.",
    "Schedule brake system inspection": "Запланировать проверку тормозной системы.",
    "Monitor; plan track inspection if persistent": "Продолжать наблюдение; при сохранении проблемы запланировать осмотр пути.",
    "Plan refueling stop": "Запланировать дозаправку.",
    "Review fault code in maintenance log": "Проверить код неисправности в журнале обслуживания.",
}

SOURCE_LABELS = {
    "openai": "OpenAI",
    "fallback": "Резервный анализ",
    "disabled": "Отключено",
    "unavailable": "Недоступно",
}

RISK_LABELS = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}


def to_russian_recommendation(value: str) -> str:
    return RECOMMENDATION_TRANSLATIONS.get(value, value)


def summary_recommendation(alerts: list[dict[str, Any]], label: str, factors: list[dict[str, Any]]) -> str:
    if alerts:
        first = alerts[0]
        recommendation = first.get("recommendation")
        if recommendation:
            return to_russian_recommendation(str(recommendation))
        return f"Проверить активный алерт: {first.get('title', 'Unknown issue')}"

    if label == "CRITICAL":
        return "Снизить нагрузку и немедленно проверить главные факторы ухудшения здоровья."
    if label == "WARNING":
        return "Следить за ключевыми факторами риска и запланировать профилактическое обслуживание."
    if factors:
        factor_name = factors[0].get("parameter", "ключевой фактор риска")
        return f"Система стабильна. Продолжать наблюдение за фактором {factor_name}."
    return "Система стабильна. Продолжать мониторинг."


def build_summary_lines(snapshot: dict[str, Any], ai_summary: AiSummaryResponse) -> list[str]:
    health = snapshot.get("health", {})
    alerts = snapshot.get("alerts", [])
    telemetry = snapshot.get("telemetry", {})
    factors = health.get("factors", [])[:5]
    recommendation = summary_recommendation(alerts, str(health.get("label", "GOOD")), factors)

    source_label = SOURCE_LABELS.get(ai_summary.source, ai_summary.source)
    risk_label = RISK_LABELS.get(ai_summary.risk_level, ai_summary.risk_level)

    lines = [
        f"Сформировано: {telemetry.get('timestamp', health.get('timestamp', 'n/a'))}",
        "",
        f"Индекс здоровья: {health.get('value', 'n/a')} ({health.get('label', 'n/a')})",
        f"Состояние: {telemetry.get('state', 'n/a')}",
        f"Скорость: {telemetry.get('speed_kmh', 'n/a')} км/ч",
        f"Тяговая мощность: {telemetry.get('traction_power_kw', 'n/a')} кВт",
        "",
        "Топ-5 факторов риска:",
    ]

    if factors:
        lines.extend(
            [
                f"{idx}. {factor.get('parameter', 'unknown')} - score {factor.get('score', 'n/a')} / weight {factor.get('weight', 'n/a')}"
                for idx, factor in enumerate(factors, start=1)
            ]
        )
    else:
        lines.append("Факторы риска не найдены.")

    lines.append("")
    lines.append("Активные алерты:")
    if alerts:
        lines.extend(
            [
                f"{idx}. [{alert.get('severity', 'info')}] {alert.get('title', 'Alert')} - {alert.get('detail') or 'Без деталей'}"
                for idx, alert in enumerate(alerts[:8], start=1)
            ]
        )
    else:
        lines.append("Нет активных алертов.")

    lines.append("")
    lines.append("Рекомендация:")
    lines.append(recommendation)
    lines.append("")
    lines.append("AI-анализ:")
    lines.append(f"Источник: {source_label}{f' ({ai_summary.model})' if ai_summary.model else ''}")
    lines.append(f"Уровень риска: {risk_label}")
    lines.append(f"Сводка AI: {ai_summary.summary}")
    lines.append(f"Прогноз: {ai_summary.forecast}")
    lines.append("Рекомендации AI:")

    if ai_summary.recommendations:
        lines.extend([f"- {item}" for item in ai_summary.recommendations[:4]])
    else:
        lines.append("Рекомендации AI недоступны.")

    return lines
