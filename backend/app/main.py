"""FastAPI application — entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import analysis, auth, streaming, telemetry
from app.services.simulator import get_simulator_service

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="KZT Locomotive Telemetry API",
    version="0.2.0",
    description="Real-time locomotive telemetry streaming, health monitoring, and analytics",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(telemetry.router)
app.include_router(streaming.router)
app.include_router(auth.router)
app.include_router(analysis.router)


# --- Startup / shutdown ---

@app.on_event("startup")
async def on_startup() -> None:
    service = get_simulator_service()
    await service.start()
    logging.getLogger(__name__).info("Simulator streaming started")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    service = get_simulator_service()
    await service.stop()


# --- Root ---

@app.get("/")
def root() -> dict:
    return {
        "service": "KZT Locomotive Telemetry API",
        "version": "0.2.0",
        "docs": "/docs",
        "endpoints": {
            "websocket": "/ws/telemetry",
            "current": "/api/v1/telemetry/current",
            "health": "/api/v1/telemetry/health",
            "history": "/api/v1/telemetry/history",
            "graph": "/api/v1/telemetry/graph",
            "simulation": "/api/v1/simulation/run",
            "export_csv": "/api/v1/telemetry/export/csv",
            "export_summary": "/api/v1/telemetry/export/summary",
            "alerts": "/api/v1/alerts",
            "ai_summary": "/api/v1/analysis/ai-summary",
            "config": "/api/v1/config",
            "health_config": "/api/v1/config/health",
        },
    }


@app.get("/health")
def health_check() -> dict:
    service = get_simulator_service()
    return {
        "status": "ok",
        "ticks_processed": service.tick_count,
        "buffer_size": len(service.processor.buffer),
    }
