"use client";

import type { TelemetryPoint, UserInfo } from "@/lib/api";

export function TopBar({
  connected,
  user,
  tel,
  liveTimestamp,
  eventsPerSecond,
  routeDistanceKm,
  routeDistanceTotalKm,
  themeMode,
  viewMode,
  playbackPaused,
  onEnterLiveMode,
  onEnterReplayMode,
  onTogglePlaybackPause,
  onToggleTheme,
  onLogout,
  exportSummaryHref,
  exportCsvHref,
  exportCsv24hHref,
  exportCsv72hHref,
  timeLabel,
}: {
  connected: boolean;
  user: UserInfo;
  tel?: TelemetryPoint;
  liveTimestamp?: string;
  eventsPerSecond: number;
  routeDistanceKm: number;
  routeDistanceTotalKm: number;
  themeMode: "light" | "dark";
  viewMode: "live" | "replay";
  playbackPaused: boolean;
  onEnterLiveMode: () => void;
  onEnterReplayMode: () => void;
  onTogglePlaybackPause: () => void;
  onToggleTheme: () => void;
  onLogout: () => Promise<void>;
  exportSummaryHref: string;
  exportCsvHref: string;
  exportCsv24hHref: string;
  exportCsv72hHref: string;
  timeLabel: (value: string) => string;
}) {
  return (
    <div className="top-bar">
      <div className="loco-id">
        <div className={`loco-dot ${connected ? "is-live" : "is-offline"}`}></div>
        <div>
          <div className="loco-name">ТЭП70БС · № 0247 · electric</div>
          <div className="loco-sub">
            Алматы → Астана · {routeDistanceKm}/{routeDistanceTotalKm} км
          </div>
        </div>
      </div>

      <div className="top-meta">
        <span>Скорость <b>{tel ? `${tel.speed_kmh.toFixed(1)} км/ч` : "—"}</b></span>
        <span>Мощность <b>{tel ? `${(tel.traction_power_kw / 1000).toFixed(2)} МВт` : "—"}</b></span>
        <span>Напряжение <b>{tel ? `${Math.round(tel.voltage_v)} В` : "—"}</b></span>
        <span>Время <b>{liveTimestamp ? timeLabel(liveTimestamp) : tel ? timeLabel(tel.timestamp) : "—"}</b></span>
        <span>Поток <b>{eventsPerSecond.toFixed(1)} evt/s</b></span>
        <span>
          <span className={`ws-badge ${connected ? "ws-on" : "ws-off"}`}>
            {connected ? "● поток онлайн" : "● нет соединения"}
          </span>
        </span>
      </div>

      <div className="top-actions">
        <span className="user-chip">{user.username}</span>
        <div className="mode-switch" role="tablist" aria-label="Режим просмотра телеметрии">
          <button className={`mode-switch-btn ${viewMode === "live" ? "active" : ""}`} type="button" onClick={onEnterLiveMode}>
            LIVE
          </button>
          <button className={`mode-switch-btn ${viewMode === "replay" ? "active" : ""}`} type="button" onClick={onEnterReplayMode}>
            REPLAY
          </button>
        </div>
        <button
          className="btn"
          type="button"
          onClick={onTogglePlaybackPause}
          disabled={viewMode === "live"}
          aria-disabled={viewMode === "live"}
          title={viewMode === "live" ? "Пауза доступна только в режиме REPLAY" : undefined}
        >
          {playbackPaused ? "▶ Продолжить" : "⏸ Пауза"}
        </button>
        <button className="btn" type="button" onClick={onToggleTheme}>
          {themeMode === "dark" ? "☀ Светлая" : "🌙 Тёмная"}
        </button>
        <button className="btn" type="button" onClick={onLogout}>
          Выйти
        </button>
        <a className="btn" href={exportSummaryHref}>
          Export Summary
        </a>
        <a className="btn btn-accent" href={exportCsvHref}>
          Экспорт CSV
        </a>
        <a className="btn btn-accent" href={exportCsv24hHref}>
          CSV 24ч
        </a>
        <a className="btn btn-accent" href={exportCsv72hHref}>
          CSV 72ч
        </a>
      </div>
    </div>
  );
}
