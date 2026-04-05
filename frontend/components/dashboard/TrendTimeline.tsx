"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartPoint } from "@/utils/dashboard";
import { REPLAY_WINDOWS, tooltipStyle } from "@/utils/dashboard";
import type { ReplayMarker } from "@/hooks/useReplayController";

export function TrendTimeline({
  chartData,
  latest,
  viewMode,
  playbackPaused,
  replayWindowMinutes,
  replayFramesLength,
  replayStartLabel,
  replayPositionLabel,
  replayMarkers,
  selectedReplayIndex,
  onReplayWindowChange,
  onReplaySliderChange,
}: {
  chartData: ChartPoint[];
  latest?: ChartPoint;
  viewMode: "live" | "replay";
  playbackPaused: boolean;
  replayWindowMinutes: (typeof REPLAY_WINDOWS)[number];
  replayFramesLength: number;
  replayStartLabel: string;
  replayPositionLabel: string;
  replayMarkers: ReplayMarker[];
  selectedReplayIndex: number;
  onReplayWindowChange: (minutes: (typeof REPLAY_WINDOWS)[number]) => void;
  onReplaySliderChange: (index: number) => void;
}) {
  return (
    <div className="timeline-card">
      <div className="section-header">
        <span className="card-title section-title">Тренды: индекс здоровья / скорость / ток</span>
        <div className="timeline-meta">
          <span>Режим: {viewMode === "live" ? "LIVE" : `REPLAY ${replayWindowMinutes} мин`}</span>
          <span>Статус: {playbackPaused ? "пауза" : viewMode === "replay" ? "воспроизведение" : "прямой эфир"}</span>
          <span>Точек: {chartData.length}</span>
          <span>Скорость: {latest ? `${latest.speed.toFixed(1)} км/ч` : "—"}</span>
          <span>Ток: {latest ? `${latest.current} А` : "—"}</span>
        </div>
      </div>
      <div className="replay-toolbar">
        <div className="replay-window-group" role="tablist" aria-label="Окно воспроизведения">
          {REPLAY_WINDOWS.map((minutes) => (
            <button
              key={minutes}
              className={`replay-window-btn ${replayWindowMinutes === minutes ? "active" : ""}`}
              type="button"
              onClick={() => onReplayWindowChange(minutes)}
            >
              {minutes} мин
            </button>
          ))}
        </div>
        <div className="replay-status">
          <span className={`badge ${viewMode === "live" ? "badge-normal" : "badge-warning"}`}>
            {viewMode === "live" ? "Прямой эфир" : "Диагностика"}
          </span>
          <span>
            {viewMode === "live"
              ? playbackPaused
                ? `Live на паузе: ${replayPositionLabel}`
                : "История пополняется автоматически"
              : playbackPaused
                ? `Replay на паузе: ${replayPositionLabel}`
                : `Replay идёт с отставанием: ${replayPositionLabel}`}
          </span>
        </div>
      </div>
      <div className={`replay-scrubber ${viewMode === "replay" ? "is-active" : ""}`}>
        <div className="replay-meta">
          <span>Начало: {replayStartLabel}</span>
          <span>Позиция: {replayPositionLabel}</span>
          <span>Алерты: {replayMarkers.length}</span>
        </div>
        <div className="replay-slider-shell">
          <input
            className="replay-slider"
            type="range"
            min={0}
            max={Math.max(replayFramesLength - 1, 0)}
            value={viewMode === "replay" ? selectedReplayIndex : Math.max(replayFramesLength - 1, 0)}
            onChange={(event) => onReplaySliderChange(Number(event.target.value))}
            disabled={replayFramesLength <= 1}
            aria-label="Позиция replay timeline"
          />
          <div className="replay-markers" aria-hidden="true">
            {replayMarkers.map((marker) => (
              <span
                key={marker.id}
                className={`replay-marker replay-marker-${marker.severity}`}
                style={{ left: `${replayFramesLength > 1 ? (marker.index / (replayFramesLength - 1)) * 100 : 0}%` }}
                title={`${marker.time} · ${marker.label}`}
              ></span>
            ))}
          </div>
        </div>
      </div>
      <div className="chart-wrap trend-wrap">
        <ResponsiveContainer>
          <LineChart data={chartData}>
            <CartesianGrid stroke="var(--grid-line)" vertical={false} />
            <XAxis dataKey="time" tick={{ fontSize: 10, fill: "var(--text-soft)" }} tickLine={false} axisLine={false} />
            <YAxis yAxisId="health" domain={[0, 100]} tick={{ fontSize: 10, fill: "var(--success)" }} tickLine={false} axisLine={false} />
            <YAxis yAxisId="speed" hide domain={[0, 100]} />
            <YAxis yAxisId="current" hide domain={[0, 1000]} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line yAxisId="health" type="monotone" dataKey="health" stroke="var(--success)" strokeWidth={2.4} dot={false} isAnimationActive={false} />
            <Line yAxisId="speed" type="monotone" dataKey="speed" stroke="var(--accent)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
            <Line yAxisId="current" type="monotone" dataKey="current" stroke="var(--danger-strong)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
