"""
Alert engine — monitors telemetry for anomalies, fires prioritized alerts
with recommendations. Deduplicates: same code won't fire again within cooldown.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.schemas import Alert


@dataclass
class _Rule:
    code: str
    severity: str            # critical / warning / info
    title: str
    recommendation: str
    check: Any               # callable(telemetry) -> str | None  (detail text or None)
    cooldown_ticks: int = 10


def _check_overheat(t: dict) -> str | None:
    eng = t.get("engine_temp_c", 0)
    xfm = t.get("transformer_temp_c", 0)
    if eng > 95:
        return f"Engine temperature critically high: {eng:.1f} C"
    if xfm > 92:
        return f"Transformer temperature critically high: {xfm:.1f} C"
    return None


def _check_overheat_warn(t: dict) -> str | None:
    eng = t.get("engine_temp_c", 0)
    xfm = t.get("transformer_temp_c", 0)
    if 85 < eng <= 95:
        return f"Engine temperature elevated: {eng:.1f} C"
    if 80 < xfm <= 92:
        return f"Transformer temperature elevated: {xfm:.1f} C"
    return None


def _check_brake_critical(t: dict) -> str | None:
    bp = t.get("brake_pipe_pressure_bar", 5)
    if bp < 3.5:
        return f"Brake pipe pressure critically low: {bp:.2f} bar"
    return None


def _check_brake_warn(t: dict) -> str | None:
    bp = t.get("brake_pipe_pressure_bar", 5)
    if 3.5 <= bp < 4.3:
        return f"Brake pipe pressure declining: {bp:.2f} bar"
    return None


def _check_vibration(t: dict) -> str | None:
    vib = t.get("vibration_mm_s", 0)
    if vib > 2.5:
        return f"Vibration critically high: {vib:.3f} mm/s"
    return None


def _check_vibration_warn(t: dict) -> str | None:
    vib = t.get("vibration_mm_s", 0)
    if 1.8 < vib <= 2.5:
        return f"Vibration elevated: {vib:.3f} mm/s"
    return None


def _check_overcurrent(t: dict) -> str | None:
    cur = t.get("current_a", 0)
    if cur > 850:
        return f"Current draw excessive: {cur:.1f} A"
    return None


def _check_voltage_critical(t: dict) -> str | None:
    voltage = t.get("voltage_v", 0)
    if voltage < 24050:
        return f"Supply voltage critically low: {voltage:.0f} V"
    return None


def _check_voltage_warn(t: dict) -> str | None:
    voltage = t.get("voltage_v", 0)
    if 24050 <= voltage < 24300:
        return f"Supply voltage sag detected: {voltage:.0f} V"
    return None


def _check_fuel_low(t: dict) -> str | None:
    fuel = t.get("fuel_level_pct", 100)
    if fuel < 10:
        return f"Fuel level critically low: {fuel:.1f}%"
    return None


def _check_fault_code(t: dict) -> str | None:
    fc = t.get("fault_code")
    if fc:
        return f"Active fault code: {fc}"
    return None


RULES: list[_Rule] = [
    _Rule("OVERHEAT_CRIT",   "critical", "Critical overheating",        "Reduce throttle immediately; inspect cooling system",          _check_overheat,       15),
    _Rule("BRAKE_CRIT",      "critical", "Brake pressure critical",     "Emergency stop procedure; check brake line integrity",         _check_brake_critical, 15),
    _Rule("VIBRATION_CRIT",  "critical", "Excessive vibration",         "Reduce speed; inspect bogies and track condition",             _check_vibration,      12),
    _Rule("OVERCURRENT",     "critical", "Electrical overload",         "Reduce traction demand; check for short circuits",             _check_overcurrent,    12),
    _Rule("VOLTAGE_CRIT",    "critical", "Voltage supply critical",     "Reduce traction load; inspect pantograph and power circuit",   _check_voltage_critical, 12),
    _Rule("OVERHEAT_WARN",   "warning",  "Temperature rising",          "Monitor closely; consider reducing load",                      _check_overheat_warn,  10),
    _Rule("BRAKE_WARN",      "warning",  "Brake pressure declining",    "Schedule brake system inspection",                             _check_brake_warn,     10),
    _Rule("VIBRATION_WARN",  "warning",  "Vibration increasing",        "Monitor; plan track inspection if persistent",                 _check_vibration_warn, 10),
    _Rule("VOLTAGE_WARN",    "warning",  "Voltage sag",                 "Monitor power supply quality and pantograph contact",          _check_voltage_warn,   10),
    _Rule("FUEL_LOW",        "warning",  "Low fuel",                    "Plan refueling stop",                                          _check_fuel_low,       20),
    _Rule("FAULT_CODE",      "info",     "Active fault code detected",  "Review fault code in maintenance log",                         _check_fault_code,     5),
]

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass
class AlertEngine:
    """Stateful alert engine — call evaluate() each tick."""

    max_active: int = 50
    _active: list[Alert] = field(default_factory=list)
    _cooldowns: dict[str, int] = field(default_factory=dict)  # code -> ticks remaining

    def evaluate(self, telemetry: dict[str, Any]) -> list[Alert]:
        """Check all rules and keep only alerts that are active for the current tick."""
        current_alerts: list[Alert] = []

        # Decrement cooldowns
        expired = [c for c, v in self._cooldowns.items() if v <= 0]
        for c in expired:
            del self._cooldowns[c]
        for c in self._cooldowns:
            self._cooldowns[c] -= 1

        for rule in RULES:
            detail = rule.check(telemetry)
            if detail is None:
                continue

            existing = next((alert for alert in self._active if alert.code == rule.code), None)
            if existing is not None:
                existing.detail = detail
                current_alerts.append(existing)
                continue

            if rule.code in self._cooldowns:
                continue

            current_alerts.append(
                Alert(
                    id=str(uuid.uuid4()),
                    ts=datetime.now(timezone.utc).isoformat(),
                    severity=rule.severity,
                    code=rule.code,
                    title=rule.title,
                    detail=detail,
                    recommendation=rule.recommendation,
                )
            )
            self._cooldowns[rule.code] = rule.cooldown_ticks

        self._active = current_alerts[: self.max_active]

        # Sort by severity
        self._active.sort(key=lambda a: SEVERITY_ORDER.get(a.severity, 9))

        return list(self._active)

    def get_active(self) -> list[Alert]:
        return list(self._active)

    def acknowledge(self, alert_id: str) -> bool:
        for a in self._active:
            if a.id == alert_id:
                a.acknowledged = True
                return True
        return False

    def clear_acknowledged(self) -> int:
        before = len(self._active)
        self._active = [a for a in self._active if not a.acknowledged]
        return before - len(self._active)
