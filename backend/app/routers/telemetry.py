"""REST endpoints for historical data, graph-ready series, config, and export."""

from __future__ import annotations

import csv
import io
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from app.core.history import (
    get_current_snapshot,
    get_processed_rows,
    get_processed_rows_by_hours,
    get_recent_frames,
    get_recent_frames_by_hours,
)
from app.core.report_summary import build_summary_lines
from app.schemas import GraphSeries, HealthConfig, HealthIndex, SimConfig, SimulationResponse
from app.services.ai_analysis_ru import get_ai_analysis_service
from app.services.auth import get_current_user_from_request
from app.services.health_configurable import compute_health, get_health_config
from app.services.reporting import build_summary_pdf
from app.services.simulator import get_simulator_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["telemetry"], dependencies=[Depends(get_current_user_from_request)])


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    if not rows:
        return StreamingResponse(
            iter(["no data\n"]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/telemetry/current")
async def get_current() -> dict:
    """Latest processed telemetry + health + alerts."""
    return get_current_snapshot()


@router.get("/telemetry/health", response_model=HealthIndex)
async def get_health() -> HealthIndex:
    """Current health index only."""
    rows = get_processed_rows(1)
    if not rows:
        return HealthIndex(value=100, label="GOOD", factors=[], timestamp="")
    return compute_health(rows[-1])


@router.get("/telemetry/history")
async def get_history(last_n: int = Query(600, ge=1, le=5000)) -> list[dict]:
    """Return last N processed frames."""
    return get_recent_frames(last_n)


@router.get("/telemetry/history/range")
async def get_history_range(hours: int = Query(24, ge=1, le=72)) -> list[dict]:
    """Return processed frames for the last N hours from persistent history."""
    return get_recent_frames_by_hours(hours)


@router.get("/telemetry/graph", response_model=GraphSeries)
async def get_graph_series(last_n: int = Query(200, ge=10, le=2000)) -> GraphSeries:
    """Return arrays ready for Recharts / any charting lib."""
    rows = get_processed_rows(last_n)

    return GraphSeries(
        ticks=list(range(len(rows))),
        speed_kmh=[r.get("speed_kmh", 0) for r in rows],
        traction_power_kw=[r.get("traction_power_kw", 0) for r in rows],
        engine_temp_c=[r.get("engine_temp_c", 0) for r in rows],
        transformer_temp_c=[r.get("transformer_temp_c", 0) for r in rows],
        brake_pipe_pressure_bar=[r.get("brake_pipe_pressure_bar", 0) for r in rows],
        vibration_mm_s=[r.get("vibration_mm_s", 0) for r in rows],
        health_index=[compute_health(r).value for r in rows],
        states=[r.get("state", "IDLE") for r in rows],
    )


@router.get("/telemetry/graph/range", response_model=GraphSeries)
async def get_graph_series_range(hours: int = Query(24, ge=1, le=72)) -> GraphSeries:
    """Return graph-ready arrays for the last N hours from persistent history."""
    rows = get_processed_rows_by_hours(hours)

    return GraphSeries(
        ticks=list(range(len(rows))),
        speed_kmh=[r.get("speed_kmh", 0) for r in rows],
        traction_power_kw=[r.get("traction_power_kw", 0) for r in rows],
        engine_temp_c=[r.get("engine_temp_c", 0) for r in rows],
        transformer_temp_c=[r.get("transformer_temp_c", 0) for r in rows],
        brake_pipe_pressure_bar=[r.get("brake_pipe_pressure_bar", 0) for r in rows],
        vibration_mm_s=[r.get("vibration_mm_s", 0) for r in rows],
        health_index=[compute_health(r).value for r in rows],
        states=[r.get("state", "IDLE") for r in rows],
    )


@router.get("/simulation/run", response_model=SimulationResponse)
async def run_simulation(
    ticks: int = Query(200, ge=10, le=2000),
    seed: int = Query(42),
    locomotive_type: str = Query("electric"),
) -> SimulationResponse:
    """Run a full scenario and return graph-ready data + quality check."""
    service = get_simulator_service()
    rows, quality = service.run_batch(ticks=ticks, seed=seed, locomotive_type=locomotive_type)

    series = GraphSeries(
        ticks=[r.get("tick", i) for i, r in enumerate(rows)],
        speed_kmh=[r["speed_kmh"] for r in rows],
        traction_power_kw=[r["traction_power_kw"] for r in rows],
        engine_temp_c=[r["engine_temp_c"] for r in rows],
        transformer_temp_c=[r["transformer_temp_c"] for r in rows],
        brake_pipe_pressure_bar=[r["brake_pipe_pressure_bar"] for r in rows],
        vibration_mm_s=[r["vibration_mm_s"] for r in rows],
        health_index=[compute_health(r).value for r in rows],
        states=[r.get("state", "IDLE") for r in rows],
    )

    return SimulationResponse(series=series, quality=quality)


@router.get("/telemetry/export/csv")
async def export_csv(last_n: int = Query(500, ge=1, le=5000)) -> StreamingResponse:
    """Export buffered telemetry as CSV download."""
    rows = get_processed_rows(last_n)
    return _csv_response(rows, "telemetry.csv")


@router.get("/telemetry/export/csv/range")
async def export_csv_range(hours: int = Query(24, ge=1, le=72)) -> StreamingResponse:
    """Export telemetry history for the last N hours as CSV download."""
    rows = get_processed_rows_by_hours(hours)
    return _csv_response(rows, f"telemetry-{hours}h.csv")


@router.get("/telemetry/export/summary")
async def export_summary_pdf() -> Response:
    """Export a compact one-page PDF summary for the current state."""
    ai_summary = get_ai_analysis_service().summarize_last_window()
    snapshot = get_current_snapshot()
    lines = build_summary_lines(snapshot, ai_summary)
    pdf = build_summary_pdf(lines, title="Краткий отчёт KTZ Digital Twin")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="telemetry-summary.pdf"'},
    )


@router.get("/alerts")
async def get_alerts() -> list[dict]:
    service = get_simulator_service()
    return [a.model_dump() for a in service.alert_engine.get_active()]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> dict:
    service = get_simulator_service()
    found = service.alert_engine.acknowledge(alert_id)
    return {"acknowledged": found}


@router.post("/simulator/state")
async def set_simulator_state(state: str = Query(...)) -> dict:
    service = get_simulator_service()
    service.set_state(state)
    return {"state": state.upper()}


@router.post("/simulator/anomaly")
async def trigger_anomaly(name: str = Query(...)) -> dict:
    service = get_simulator_service()
    service.trigger_anomaly(name)
    return {"anomaly": name.upper()}


@router.get("/config", response_model=SimConfig)
async def get_config() -> SimConfig:
    from app.config import get_settings

    settings = get_settings()
    return SimConfig(
        tick_interval_s=settings.sim_tick_interval_s,
        locomotive_type=settings.sim_locomotive_type,
        ema_alpha=settings.ema_alpha,
    )


@router.get("/config/health", response_model=HealthConfig)
async def get_health_index_config() -> HealthConfig:
    return get_health_config()
