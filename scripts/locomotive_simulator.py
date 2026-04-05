"""
Stateful locomotive telemetry simulator for dashboard demos.

Generates realistic telemetry streams (speed, power, temperatures, brake pressure,
vibration, etc.) that transition smoothly between operating states.

Can be used standalone::

    python scripts/locomotive_simulator.py          # prints JSON lines
    python scripts/locomotive_simulator.py --ticks 200 --interval 0.3

Or imported::

    from locomotive_simulator import LocomotiveSimulator
    sim = LocomotiveSimulator()
    sim.init()
    sim.set_target_state("CRUISING")
    for _ in range(100):
        print(sim.update())
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional


class LocomotiveSimulator:
    """Stateful locomotive telemetry simulator for dashboard demos."""

    IDLE = "IDLE"
    ACCELERATING = "ACCELERATING"
    CRUISING = "CRUISING"
    BRAKING = "BRAKING"

    VALID_STATES = {IDLE, ACCELERATING, CRUISING, BRAKING}
    VALID_ANOMALIES = {
        "OVERHEAT",
        "BRAKE_PRESSURE_DROP",
        "HIGH_VIBRATION",
        "VOLTAGE_SAG",
        "OVERCURRENT_SPIKE",
        "FUEL_LEAK",
    }

    def init(self, locomotive_type: str = "electric", seed: Optional[int] = None) -> None:
        self.random = random.Random(seed)
        self.locomotive_type = locomotive_type.lower()
        self.state = self.IDLE
        self.target_state = self.IDLE
        self.tick_count = 0
        self.cruise_target_speed = self.random.uniform(58.0, 72.0)
        self.active_anomaly: Optional[str] = None
        self.anomaly_ticks_remaining = 0

        self.telemetry: Dict[str, Optional[float]] = {
            "speed_kmh": 0.3,
            "traction_power_kw": 50.0,
            "engine_temp_c": 52.0,
            "transformer_temp_c": 48.0,
            "brake_pipe_pressure_bar": 5.0,
            "voltage_v": 24750.0,
            "current_a": 90.0,
            "vibration_mm_s": 0.35,
            "fuel_level_pct": 96.0,
            "fault_code": None,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_target_state(self, new_state: str) -> None:
        """Request a final state; the simulator chooses the transition path."""
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Unsupported state: {new_state}")

        self.target_state = new_state

        if new_state == self.CRUISING:
            self.cruise_target_speed = self.random.uniform(58.0, 78.0)
        elif new_state == self.ACCELERATING:
            self.cruise_target_speed = self.random.uniform(68.0, 84.0)

    def set_state(self, new_state: str) -> None:
        """Backward-compatible alias."""
        self.set_target_state(new_state)

    def trigger_anomaly(self, name: str) -> None:
        if name not in self.VALID_ANOMALIES:
            raise ValueError(f"Unsupported anomaly: {name}")
        self.active_anomaly = name
        self.anomaly_ticks_remaining = {
            "OVERHEAT": 24,
            "BRAKE_PRESSURE_DROP": 10,
            "HIGH_VIBRATION": 12,
            "VOLTAGE_SAG": 14,
            "OVERCURRENT_SPIKE": 10,
            "FUEL_LEAK": 16,
        }[name]

    def refuel_full(self) -> None:
        """Refill fuel to 100% for demo/operator recovery scenarios."""
        self.telemetry["fuel_level_pct"] = 100.0
        if self.active_anomaly == "FUEL_LEAK":
            self.active_anomaly = None
            self.anomaly_ticks_remaining = 0
        if self.telemetry.get("fault_code") == "FUEL_LEAK":
            self.telemetry["fault_code"] = None

    def update(self) -> Dict[str, Optional[float]]:
        self.tick_count += 1

        self._advance_state_machine()
        self._apply_state_dynamics()
        self._apply_correlations()
        self._maybe_trigger_random_anomaly()
        self._apply_anomaly()
        self._apply_micro_variation()
        self._update_fault_code()
        self._enforce_bounds()

        values = self.telemetry
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self.state,
            "speed_kmh": round(values["speed_kmh"], 2),
            "traction_power_kw": round(values["traction_power_kw"], 2),
            "engine_temp_c": round(values["engine_temp_c"], 2),
            "transformer_temp_c": round(values["transformer_temp_c"], 2),
            "brake_pipe_pressure_bar": round(values["brake_pipe_pressure_bar"], 3),
            "voltage_v": round(values["voltage_v"], 2),
            "current_a": round(values["current_a"], 2),
            "vibration_mm_s": round(values["vibration_mm_s"], 3),
            "fuel_level_pct": round(values["fuel_level_pct"], 3),
            "fault_code": values["fault_code"],
        }

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _advance_state_machine(self) -> None:
        speed = self.telemetry["speed_kmh"]
        nearly_stopped = speed <= 1.0
        near_cruise = abs(speed - self.cruise_target_speed) <= 2.5

        if self.target_state == self.IDLE:
            self.state = self.IDLE if nearly_stopped else self.BRAKING
            return

        if self.target_state == self.BRAKING:
            self.state = self.IDLE if nearly_stopped else self.BRAKING
            return

        if self.target_state == self.ACCELERATING:
            if speed > self.cruise_target_speed + 4.0:
                self.state = self.BRAKING
            elif speed >= max(self.cruise_target_speed - 5.0, 45.0):
                self.state = self.CRUISING
            else:
                self.state = self.ACCELERATING
            return

        if self.target_state == self.CRUISING:
            if nearly_stopped:
                self.state = self.ACCELERATING
            elif speed < self.cruise_target_speed - 3.0:
                self.state = self.ACCELERATING
            elif speed > self.cruise_target_speed + 4.0:
                self.state = self.BRAKING
            elif near_cruise:
                self.state = self.CRUISING
            else:
                self.state = self.ACCELERATING if speed < self.cruise_target_speed else self.BRAKING

    # ------------------------------------------------------------------
    # Per-state dynamics
    # ------------------------------------------------------------------

    def _apply_state_dynamics(self) -> None:
        if self.state == self.IDLE:
            self._update_idle()
        elif self.state == self.ACCELERATING:
            self._update_accelerating()
        elif self.state == self.CRUISING:
            self._update_cruising()
        elif self.state == self.BRAKING:
            self._update_braking()

    def _update_idle(self) -> None:
        v = self.telemetry
        v["speed_kmh"] = self._approach(v["speed_kmh"], self.random.uniform(0.0, 0.4), 0.35, 0.04)
        v["traction_power_kw"] = self._approach(v["traction_power_kw"], self.random.uniform(20.0, 100.0), 0.12, 5.0)
        v["current_a"] = self._approach(v["current_a"], self.random.uniform(70.0, 120.0), 0.16, 3.0)
        v["engine_temp_c"] = self._approach(v["engine_temp_c"], self.random.uniform(48.0, 56.0), 0.025, 0.03)
        v["transformer_temp_c"] = self._approach(v["transformer_temp_c"], self.random.uniform(44.0, 52.0), 0.025, 0.03)
        v["brake_pipe_pressure_bar"] = self._approach(v["brake_pipe_pressure_bar"], self.random.uniform(4.97, 5.05), 0.14, 0.008)
        v["vibration_mm_s"] = self._approach(v["vibration_mm_s"], self.random.uniform(0.25, 0.55), 0.18, 0.02)
        v["fuel_level_pct"] -= self.random.uniform(0.0005, 0.0015)
        v["voltage_v"] = self._approach(v["voltage_v"], self.random.uniform(24670.0, 24830.0), 0.14, 4.0)

    def _update_accelerating(self) -> None:
        v = self.telemetry
        accel_target = min(self.cruise_target_speed + self.random.uniform(2.0, 6.0), 86.0)
        v["speed_kmh"] = self._approach(v["speed_kmh"], accel_target, 0.09, 0.22)
        v["traction_power_kw"] = self._approach(v["traction_power_kw"], self.random.uniform(3200.0, 5600.0), 0.12, 60.0)
        v["current_a"] = self._approach(v["current_a"], self.random.uniform(520.0, 860.0), 0.13, 10.0)
        v["engine_temp_c"] = self._approach(v["engine_temp_c"], self.random.uniform(68.0, 84.0), 0.03, 0.05)
        v["transformer_temp_c"] = self._approach(v["transformer_temp_c"], self.random.uniform(62.0, 80.0), 0.035, 0.05)
        v["brake_pipe_pressure_bar"] = self._approach(v["brake_pipe_pressure_bar"], self.random.uniform(4.92, 5.08), 0.09, 0.012)
        v["vibration_mm_s"] = self._approach(v["vibration_mm_s"], self.random.uniform(1.0, 2.0), 0.12, 0.03)
        v["fuel_level_pct"] -= self.random.uniform(0.007, 0.014)
        v["voltage_v"] = self._approach(v["voltage_v"], self.random.uniform(24560.0, 24810.0), 0.12, 7.0)

    def _update_cruising(self) -> None:
        v = self.telemetry
        v["speed_kmh"] = self._approach(v["speed_kmh"], self.cruise_target_speed + self.random.uniform(-1.0, 1.0), 0.12, 0.12)
        v["traction_power_kw"] = self._approach(v["traction_power_kw"], self.random.uniform(1800.0, 3200.0), 0.1, 35.0)
        v["current_a"] = self._approach(v["current_a"], self.random.uniform(360.0, 560.0), 0.11, 7.0)
        v["engine_temp_c"] = self._approach(v["engine_temp_c"], self.random.uniform(72.0, 84.0), 0.02, 0.03)
        v["transformer_temp_c"] = self._approach(v["transformer_temp_c"], self.random.uniform(66.0, 78.0), 0.02, 0.03)
        v["brake_pipe_pressure_bar"] = self._approach(v["brake_pipe_pressure_bar"], self.random.uniform(4.98, 5.03), 0.12, 0.008)
        v["vibration_mm_s"] = self._approach(v["vibration_mm_s"], self.random.uniform(0.7, 1.3), 0.1, 0.02)
        v["fuel_level_pct"] -= self.random.uniform(0.004, 0.009)
        v["voltage_v"] = self._approach(v["voltage_v"], self.random.uniform(24610.0, 24810.0), 0.12, 5.0)

    def _update_braking(self) -> None:
        v = self.telemetry
        brake_target = self.random.uniform(0.0, 0.8) if self.target_state in {self.IDLE, self.BRAKING} else self.cruise_target_speed - 4.0
        v["speed_kmh"] = self._approach(v["speed_kmh"], brake_target, 0.11, 0.18)
        v["traction_power_kw"] = self._approach(v["traction_power_kw"], self.random.uniform(10.0, 180.0), 0.15, 20.0)
        v["current_a"] = self._approach(v["current_a"], self.random.uniform(80.0, 220.0), 0.14, 7.0)
        v["engine_temp_c"] = self._approach(v["engine_temp_c"], self.random.uniform(58.0, 76.0), 0.02, 0.03)
        v["transformer_temp_c"] = self._approach(v["transformer_temp_c"], self.random.uniform(54.0, 70.0), 0.025, 0.03)
        v["brake_pipe_pressure_bar"] = self._approach(v["brake_pipe_pressure_bar"], self.random.uniform(4.15, 4.65), 0.2, 0.03)
        v["vibration_mm_s"] = self._approach(v["vibration_mm_s"], self.random.uniform(0.7, 1.6), 0.12, 0.03)
        v["fuel_level_pct"] -= self.random.uniform(0.0015, 0.004)
        v["voltage_v"] = self._approach(v["voltage_v"], self.random.uniform(24600.0, 24800.0), 0.1, 6.0)

    # ------------------------------------------------------------------
    # Cross-signal correlations
    # ------------------------------------------------------------------

    def _apply_correlations(self) -> None:
        v = self.telemetry
        power = v["traction_power_kw"]
        speed = v["speed_kmh"]

        target_current = 90.0 + power * 0.125 + self.random.uniform(-10.0, 10.0)
        if self.state == self.BRAKING:
            target_current *= 0.62
        v["current_a"] = self._approach(v["current_a"], target_current, 0.14, 4.0)

        load_factor = v["current_a"] / 900.0
        cooling_bias = 0.0 if self.state in {self.ACCELERATING, self.CRUISING} else 0.1

        engine_heat_target = 49.0 + load_factor * 36.0 + speed * 0.05
        transformer_heat_target = 46.0 + load_factor * 40.0

        if self.locomotive_type == "diesel":
            engine_heat_target += 5.0
        else:
            transformer_heat_target += 4.0

        v["engine_temp_c"] = self._approach(v["engine_temp_c"], engine_heat_target, 0.03 - cooling_bias * 0.08, 0.03)
        v["transformer_temp_c"] = self._approach(v["transformer_temp_c"], transformer_heat_target, 0.032 - cooling_bias * 0.08, 0.03)

        moving_consumption = 0.001 + speed * 0.000025
        if self.state == self.ACCELERATING:
            moving_consumption += 0.0025
        elif self.state == self.CRUISING:
            moving_consumption += 0.0012
        v["fuel_level_pct"] -= moving_consumption

        vibration_target = 0.25 + speed * 0.01 + power / 4500.0
        if self.state == self.BRAKING:
            vibration_target += 0.18
        v["vibration_mm_s"] = self._approach(v["vibration_mm_s"], vibration_target, 0.08, 0.02)

    def _apply_micro_variation(self) -> None:
        """Add soft periodic fluctuations so the stream looks less artificially flat."""
        v = self.telemetry
        t = self.tick_count

        if self.state == self.IDLE:
            speed_wave = 0.03
            power_wave = 4.0
            temp_wave = 0.08
            pressure_wave = 0.003
            voltage_wave = 10.0
            current_wave = 2.5
            vibration_wave = 0.01
        elif self.state == self.ACCELERATING:
            speed_wave = 0.22
            power_wave = 55.0
            temp_wave = 0.25
            pressure_wave = 0.012
            voltage_wave = 22.0
            current_wave = 10.0
            vibration_wave = 0.03
        elif self.state == self.CRUISING:
            speed_wave = 0.18
            power_wave = 42.0
            temp_wave = 0.18
            pressure_wave = 0.007
            voltage_wave = 16.0
            current_wave = 7.0
            vibration_wave = 0.025
        else:
            speed_wave = 0.14
            power_wave = 18.0
            temp_wave = 0.14
            pressure_wave = 0.02
            voltage_wave = 14.0
            current_wave = 5.0
            vibration_wave = 0.025

        v["speed_kmh"] += math.sin(t * 0.31) * speed_wave + self.random.uniform(-speed_wave * 0.35, speed_wave * 0.35)
        v["traction_power_kw"] += math.sin(t * 0.23 + 0.4) * power_wave + self.random.uniform(-power_wave * 0.22, power_wave * 0.22)
        v["engine_temp_c"] += math.sin(t * 0.17 + 0.6) * temp_wave + self.random.uniform(-temp_wave * 0.4, temp_wave * 0.4)
        v["transformer_temp_c"] += math.sin(t * 0.19 + 1.1) * temp_wave + self.random.uniform(-temp_wave * 0.45, temp_wave * 0.45)
        v["brake_pipe_pressure_bar"] += math.sin(t * 0.29 + 0.2) * pressure_wave + self.random.uniform(-pressure_wave * 0.5, pressure_wave * 0.5)
        v["voltage_v"] += math.sin(t * 0.21 + 0.8) * voltage_wave + self.random.uniform(-voltage_wave * 0.35, voltage_wave * 0.35)
        v["current_a"] += math.sin(t * 0.27 + 1.3) * current_wave + self.random.uniform(-current_wave * 0.4, current_wave * 0.4)
        v["vibration_mm_s"] += math.sin(t * 0.35 + 0.5) * vibration_wave + self.random.uniform(-vibration_wave * 0.5, vibration_wave * 0.5)

    # ------------------------------------------------------------------
    # Anomaly injection
    # ------------------------------------------------------------------

    def _maybe_trigger_random_anomaly(self) -> None:
        """Roughly once per minute, trigger one random anomaly with 50% probability."""
        if self.active_anomaly is not None:
            return
        if self.tick_count <= 0 or self.tick_count % 60 != 0:
            return
        if self.random.random() >= 0.5:
            return

        anomaly_name = self.random.choice(tuple(self.VALID_ANOMALIES))
        self.trigger_anomaly(anomaly_name)

    def _apply_anomaly(self) -> None:
        if not self.active_anomaly:
            return

        v = self.telemetry
        name = self.active_anomaly

        if name == "OVERHEAT":
            v["engine_temp_c"] += self.random.uniform(1.4, 2.3)
            v["transformer_temp_c"] += self.random.uniform(1.3, 2.2)
            v["current_a"] += self.random.uniform(28.0, 52.0)
            v["traction_power_kw"] += self.random.uniform(120.0, 260.0)
            v["vibration_mm_s"] += self.random.uniform(0.03, 0.08)
        elif name == "BRAKE_PRESSURE_DROP":
            v["brake_pipe_pressure_bar"] -= self.random.uniform(0.15, 0.28)
            v["vibration_mm_s"] += self.random.uniform(0.02, 0.06)
        elif name == "HIGH_VIBRATION":
            v["vibration_mm_s"] += self.random.uniform(0.15, 0.35)
            v["speed_kmh"] = max(0.0, v["speed_kmh"] - self.random.uniform(0.05, 0.25))
        elif name == "VOLTAGE_SAG":
            v["voltage_v"] -= self.random.uniform(95.0, 180.0)
            v["current_a"] += self.random.uniform(12.0, 30.0)
            v["traction_power_kw"] = max(0.0, v["traction_power_kw"] - self.random.uniform(80.0, 220.0))
        elif name == "OVERCURRENT_SPIKE":
            v["current_a"] += self.random.uniform(75.0, 130.0)
            v["traction_power_kw"] += self.random.uniform(220.0, 520.0)
            v["transformer_temp_c"] += self.random.uniform(0.5, 1.1)
            v["engine_temp_c"] += self.random.uniform(0.2, 0.6)
        elif name == "FUEL_LEAK":
            v["fuel_level_pct"] -= self.random.uniform(4.5, 6.5)
            v["engine_temp_c"] += self.random.uniform(0.1, 0.35)
            v["traction_power_kw"] = max(0.0, v["traction_power_kw"] - self.random.uniform(20.0, 90.0))

        v["voltage_v"] += self.random.uniform(-35.0, 35.0)
        self.anomaly_ticks_remaining -= 1

        if self.anomaly_ticks_remaining <= 0:
            self.active_anomaly = None

    def _update_fault_code(self) -> None:
        v = self.telemetry
        fault = None

        if self.active_anomaly:
            fault = self.active_anomaly
        elif v["engine_temp_c"] > 92.0 or v["transformer_temp_c"] > 90.0:
            if self.random.random() < 0.6:
                fault = "OVERHEAT"
        elif v["brake_pipe_pressure_bar"] < 4.2:
            if self.random.random() < 0.7:
                fault = "BRAKE_PRESSURE_DROP"
        elif v["vibration_mm_s"] > 2.2:
            if self.random.random() < 0.65:
                fault = "HIGH_VIBRATION"
        elif v["voltage_v"] < 24200.0:
            if self.random.random() < 0.7:
                fault = "VOLTAGE_SAG"
        elif v["current_a"] > 840.0:
            if self.random.random() < 0.75:
                fault = "OVERCURRENT_SPIKE"
        elif v["fuel_level_pct"] < 20.0:
            if self.random.random() < 0.7:
                fault = "FUEL_LEAK"

        v["fault_code"] = fault

    # ------------------------------------------------------------------
    # Bounds
    # ------------------------------------------------------------------

    def _enforce_bounds(self) -> None:
        v = self.telemetry
        v["speed_kmh"] = self._clamp(v["speed_kmh"], 0.0, 90.0)
        v["traction_power_kw"] = self._clamp(v["traction_power_kw"], 0.0, 6200.0)
        v["engine_temp_c"] = self._clamp(v["engine_temp_c"], 35.0, 110.0)
        v["transformer_temp_c"] = self._clamp(v["transformer_temp_c"], 35.0, 110.0)
        v["brake_pipe_pressure_bar"] = self._clamp(v["brake_pipe_pressure_bar"], 2.5, 5.4)
        v["voltage_v"] = self._clamp(v["voltage_v"], 23800.0, 25200.0)
        v["current_a"] = self._clamp(v["current_a"], 40.0, 980.0)
        v["vibration_mm_s"] = self._clamp(v["vibration_mm_s"], 0.1, 3.5)
        v["fuel_level_pct"] = self._clamp(v["fuel_level_pct"], 0.0, 100.0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _approach(self, current: float, target: float, smoothing: float, noise: float) -> float:
        smoothing = self._clamp(smoothing, 0.02, 0.6)
        return current + (target - current) * smoothing + self.random.uniform(-noise, noise)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))


# ------------------------------------------------------------------
# Quality check — simple power-balance formula
# ------------------------------------------------------------------

def simple_quality_check(rows: list[dict], dt: float = 1.0) -> dict:
    """
    For each tick, check:  P_expected ≈ F_traction * v
    where F_traction is estimated from  current * voltage.

    Returns a summary dict with pass/fail and per-tick residuals.
    """
    if len(rows) < 2:
        return {"passed": False, "message": "Not enough data", "residuals": [], "fault_ticks": 0}

    residuals = []
    fault_ticks = 0

    for row in rows:
        speed_ms = row["speed_kmh"] / 3.6
        reported_power = row["traction_power_kw"] * 1000  # W
        electrical_power = row["current_a"] * row["voltage_v"]  # V*A = W

        if electrical_power > 0:
            ratio = reported_power / electrical_power
        else:
            ratio = 1.0  # idle, no meaningful check

        residuals.append(abs(1.0 - ratio))

        if row.get("fault_code"):
            fault_ticks += 1

    avg_residual = sum(residuals) / len(residuals)
    max_residual = max(residuals)
    passed = avg_residual < 0.25 and fault_ticks == 0

    return {
        "passed": passed,
        "avg_residual": round(avg_residual, 4),
        "max_residual": round(max_residual, 4),
        "fault_ticks": fault_ticks,
        "total_ticks": len(rows),
        "message": (
            f"avg_residual={avg_residual:.4f} (threshold 0.25), "
            f"max_residual={max_residual:.4f}, "
            f"fault_ticks={fault_ticks}/{len(rows)}"
        ),
    }


# ------------------------------------------------------------------
# Scenario runner (generates N ticks through state transitions)
# ------------------------------------------------------------------

def run_scenario(
    ticks: int = 200,
    seed: int = 42,
    locomotive_type: str = "electric",
) -> list[dict]:
    """
    Run a demo scenario: IDLE → ACCELERATING → CRUISING → BRAKING → IDLE.
    Returns a list of telemetry dicts (one per tick).
    """
    sim = LocomotiveSimulator()
    sim.init(locomotive_type=locomotive_type, seed=seed)

    schedule = [
        (0, "ACCELERATING"),
        (int(ticks * 0.15), "CRUISING"),
        (int(ticks * 0.65), "BRAKING"),
        (int(ticks * 0.85), "IDLE"),
    ]

    rows = []
    sched_idx = 0
    for tick in range(ticks):
        while sched_idx < len(schedule) and tick >= schedule[sched_idx][0]:
            sim.set_target_state(schedule[sched_idx][1])
            sched_idx += 1

        row = sim.update()
        row["tick"] = tick
        rows.append(row)

    return rows


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def _cli_listener(simulator: LocomotiveSimulator, stop_event: threading.Event) -> None:
    help_text = (
        "Commands: idle, accelerating, cruising, braking, "
        "anomaly OVERHEAT|BRAKE_PRESSURE_DROP|HIGH_VIBRATION|VOLTAGE_SAG|OVERCURRENT_SPIKE|FUEL_LEAK, quit"
    )
    print(help_text, flush=True)

    while not stop_event.is_set():
        try:
            raw = input().strip()
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            return

        if not raw:
            continue

        command = raw.upper()
        if command == "QUIT":
            stop_event.set()
            return

        if command in LocomotiveSimulator.VALID_STATES:
            simulator.set_target_state(command)
            continue

        if command.startswith("ANOMALY "):
            _, _, anomaly_name = command.partition(" ")
            if anomaly_name in LocomotiveSimulator.VALID_ANOMALIES:
                simulator.trigger_anomaly(anomaly_name)
            continue

        print(help_text, flush=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Locomotive telemetry simulator")
    parser.add_argument("--ticks", type=int, default=0, help="Run N ticks then exit (0 = interactive)")
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between ticks")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed")
    parser.add_argument("--type", default="electric", choices=["electric", "diesel"])
    args = parser.parse_args()

    sim = LocomotiveSimulator()
    sim.init(locomotive_type=args.type, seed=args.seed)
    sim.set_target_state("CRUISING")

    if args.ticks > 0:
        for _ in range(args.ticks):
            print(json.dumps(sim.update()))
            time.sleep(args.interval)
        return

    stop = threading.Event()
    listener = threading.Thread(target=_cli_listener, args=(sim, stop), daemon=True)
    listener.start()

    try:
        while not stop.is_set():
            print(json.dumps(sim.update()), flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
