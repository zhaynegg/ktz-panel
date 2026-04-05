"""Application configuration — driven by environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Supabase / Postgres ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_auth_enabled: bool = False
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kzt"

    # --- Auth ---
    
    auth_enabled: bool = True
    auth_username: str = "admin"
    auth_password: str = "admin123"
    session_cookie_name: str = "ktz_session"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Simulator ---
    sim_tick_interval_s: float = 1.0   # >= 1 Hz streaming
    sim_locomotive_type: str = "electric"
    sim_seed: int | None = None

    # --- Processing ---
    ema_alpha: float = 0.3             # EMA smoothing factor (0‑1)
    telemetry_buffer_size: int = 1800  # keep last N ticks in memory (~30 min @ 1 Hz)
    telemetry_history_db_path: str = str(Path(__file__).resolve().parents[1] / "data" / "telemetry_history.sqlite3")
    telemetry_history_retention_hours: int = 72
    health_config_path: str = str(Path(__file__).resolve().parents[1] / "config" / "health_index.json")
    ai_analysis_enabled: bool = True
    ai_analysis_window_minutes: int = 10
    ai_analysis_cache_seconds: int = 600
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
