"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Telemetry ---

class TelemetryPoint(BaseModel):
    timestamp: str
    state: str
    speed_kmh: float
    traction_power_kw: float
    engine_temp_c: float
    transformer_temp_c: float
    brake_pipe_pressure_bar: float
    voltage_v: float
    current_a: float
    vibration_mm_s: float
    fuel_level_pct: float
    fault_code: Optional[str] = None


class SmoothedTelemetry(TelemetryPoint):
    """Telemetry after EMA / validation processing."""
    raw_speed_kmh: float = 0.0
    raw_engine_temp_c: float = 0.0


# --- Health index ---

class HealthFactor(BaseModel):
    parameter: str
    score: float       # 0-100 contribution
    weight: float
    detail: str


class HealthIndex(BaseModel):
    value: float                    # 0-100
    label: str                      # GOOD / WARNING / CRITICAL
    factors: list[HealthFactor]
    timestamp: str


class HealthThresholds(BaseModel):
    good_min: float
    warning_min: float


class HealthParameterConfig(BaseModel):
    weight: float
    ideal: float
    warn: float
    crit: float
    higher_is_worse: bool


class HealthConfig(BaseModel):
    thresholds: HealthThresholds
    parameters: dict[str, HealthParameterConfig]


class AiMetricStats(BaseModel):
    min: float
    max: float
    avg: float
    trend: str


class AiSummaryResponse(BaseModel):
    enabled: bool = True
    available: bool = True
    source: str = "ai"
    model: Optional[str] = None
    generated_at: str
    window_minutes: int
    risk_level: str
    summary: str
    forecast: str
    recommendations: list[str]
    current_health: float
    previous_health: float
    health_delta: float
    active_alerts_count: int
    metrics: dict[str, AiMetricStats]


# --- Alerts ---

class Alert(BaseModel):
    id: str
    ts: str
    severity: str           # critical / warning / info
    code: str
    title: str
    detail: Optional[str] = None
    recommendation: Optional[str] = None
    acknowledged: bool = False


# --- Streaming frame (WebSocket payload) ---

class StreamFrame(BaseModel):
    telemetry: SmoothedTelemetry
    health: HealthIndex
    alerts: list[Alert]


# --- Historical / export ---

class HistoryQuery(BaseModel):
    locomotive_id: str = "loco-1"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: int = 500


class GraphSeries(BaseModel):
    """Pre-processed series ready for frontend charts."""
    ticks: list[int]
    speed_kmh: list[float]
    traction_power_kw: list[float]
    engine_temp_c: list[float]
    transformer_temp_c: list[float]
    brake_pipe_pressure_bar: list[float]
    vibration_mm_s: list[float]
    health_index: list[float]
    states: list[str]


class QualityResult(BaseModel):
    passed: bool
    avg_residual: float
    max_residual: float
    fault_ticks: int
    total_ticks: int
    message: str


class SimulationResponse(BaseModel):
    series: GraphSeries
    quality: QualityResult


# --- Config ---

class SimConfig(BaseModel):
    tick_interval_s: float = 1.0
    locomotive_type: str = "electric"
    ema_alpha: float = 0.3
