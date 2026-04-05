"use client";

import { useMemo, useState } from "react";
import { useTelemetryStream } from "@/lib/useWebSocket";
import { exportCsvRangeUrl, exportCsvUrl, exportSummaryUrl, type Alert, type HealthIndex, type UserInfo } from "@/lib/api";
import { useReplayController } from "@/hooks/useReplayController";
import { TopBar } from "@/components/dashboard/TopBar";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { ChartsRow } from "@/components/dashboard/ChartsRow";
import { TrendTimeline } from "@/components/dashboard/TrendTimeline";
import { GaugePanel } from "@/components/dashboard/GaugePanel";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { LocomotiveSchematic } from "@/components/dashboard/LocomotiveSchematic";
import {
  MAX_POINTS,
  ROUTE_DISTANCE_KM,
  type ChartPoint,
  type GaugeConfig,
  clamp01,
  computeFuelRate,
  computeRouteDistanceKm,
  currentColor,
  currentLabel,
  fuelColor,
  healthColor,
  healthStatusLabel,
  round,
  routePointAt,
  stateTone,
  timeLabel,
  vibrationColor,
  vibrationLabel,
  FAULT_LABELS,
  STATE_LABELS,
} from "@/utils/dashboard";

type DashboardViewProps = {
  user: UserInfo;
  onLogout: () => Promise<void>;
  themeMode: "light" | "dark";
  onToggleTheme: () => void;
};

export function DashboardView({ user, onLogout, themeMode, onToggleTheme }: DashboardViewProps) {
  const { connected, frame, history, send } = useTelemetryStream(true);
  const [loadMultiplier, setLoadMultiplier] = useState<1 | 5 | 10>(1);
  const {
    viewMode,
    replayWindowMinutes,
    playbackPaused,
    replayFrames,
    selectedReplayIndex,
    activeFrame,
    activeHistory,
    replayMarkers,
    togglePlaybackPause,
    enterLiveMode,
    enterReplayMode,
    handleReplayWindowChange,
    handleReplaySliderChange,
  } = useReplayController({ frame, history });

  const tel = activeFrame?.telemetry;
  const health = activeFrame?.health as HealthIndex | undefined;
  const alerts = (activeFrame?.alerts ?? []) as Alert[];
  const healthValue = health?.value ?? 0;
  const healthTone = healthColor(healthValue, health?.label);
  const fuelRate = computeFuelRate(activeHistory);
  const routeDistanceKm = Math.round(computeRouteDistanceKm(activeHistory, ROUTE_DISTANCE_KM));
  const routeProgress = clamp01(routeDistanceKm / ROUTE_DISTANCE_KM);
  const routePoint = routePointAt(routeProgress);
  const replayPositionLabel = activeFrame ? timeLabel(activeFrame.telemetry.timestamp) : "—";
  const eventsPerSecond = useMemo(() => {
    const sample = history.slice(-200);
    if (sample.length < 2) return 0;

    const end = new Date(sample[sample.length - 1]?.telemetry.timestamp ?? "").getTime();
    const startCutoff = end - 5000;
    if (!Number.isFinite(end)) return 0;

    const recent = sample.filter((entry) => {
      const time = new Date(entry.telemetry.timestamp).getTime();
      return Number.isFinite(time) && time >= startCutoff;
    });

    if (recent.length < 2) return recent.length;

    const start = new Date(recent[0].telemetry.timestamp).getTime();
    const durationSec = Math.max((end - start) / 1000, 1);
    return recent.length / durationSec;
  }, [history]);

  const chartData = useMemo<ChartPoint[]>(
    () =>
      activeHistory.slice(-MAX_POINTS).map((entry) => ({
        time: timeLabel(entry.telemetry.timestamp),
        speed: round(entry.telemetry.speed_kmh, 1),
        current: Math.round(entry.telemetry.current_a),
        engineTemp: round(entry.telemetry.engine_temp_c, 1),
        transformerTemp: round(entry.telemetry.transformer_temp_c, 1),
        brakePressure: round(entry.telemetry.brake_pipe_pressure_bar, 2),
        health: round(entry.health.value, 1),
      })),
    [activeHistory],
  );

  const latest = chartData[chartData.length - 1];
  const topFactors = (health?.factors ?? []).slice(0, 4);
  const topCriticalAlert = alerts.find((alert) => alert.severity === "critical");

  const temperatureGauges: GaugeConfig[] = tel
    ? [
        { id: "engine-temp", label: "Темп. двиг. (норма < 85°C)", value: `${tel.engine_temp_c.toFixed(1)} °C`, fill: clamp01((tel.engine_temp_c - 35) / 75) },
        { id: "trans-temp", label: "Темп. трансф. (норма < 80°C)", value: `${tel.transformer_temp_c.toFixed(1)} °C`, fill: clamp01((tel.transformer_temp_c - 35) / 75) },
        { id: "brake-pressure", label: "Давл. тормоза (норма > 4.3)", value: `${tel.brake_pipe_pressure_bar.toFixed(2)} бар`, fill: clamp01((tel.brake_pipe_pressure_bar - 2.5) / 3), inverted: true },
        { id: "vibration", label: "Вибрация (норма < 1.8)", value: `${tel.vibration_mm_s.toFixed(2)} мм/с`, fill: clamp01(tel.vibration_mm_s / 3.5) },
      ]
    : [];

  const electricGauges: GaugeConfig[] = tel
    ? [
        { id: "voltage", label: "Напряжение", value: `${Math.round(tel.voltage_v)} В`, fill: clamp01((tel.voltage_v - 23800) / 1400), fixedColor: "var(--info-strong)" },
        { id: "current", label: "Ток тяги", value: `${Math.round(tel.current_a)} А`, fill: clamp01(tel.current_a / 980) },
        { id: "power", label: "Тяговая мощность", value: `${Math.round(tel.traction_power_kw)} кВт`, fill: clamp01(tel.traction_power_kw / 6200) },
        { id: "fault", label: "Код неисправности", value: tel.fault_code ?? "Норма", fill: tel.fault_code ? 1 : 0.08, fixedColor: tel.fault_code ? "var(--danger-strong)" : "var(--success)" },
      ]
    : [];

  const fuelGauges: GaugeConfig[] = tel
    ? [
        { id: "fuel", label: "Уровень топлива", value: `${tel.fuel_level_pct.toFixed(1)} %`, fill: clamp01(tel.fuel_level_pct / 100), inverted: true },
        { id: "fuel-rate", label: "Расход (оценка)", value: fuelRate === null ? "—" : `${fuelRate.toFixed(1)} л/ч`, fill: clamp01((fuelRate ?? 0) / 50), fixedColor: "var(--info-strong)" },
        { id: "health", label: "Индекс здоровья", value: health ? `${health.value.toFixed(1)}` : "—", fill: clamp01(healthValue / 100), inverted: true },
        { id: "stream", label: "Статус потока", value: connected ? "LIVE" : "OFFLINE", fill: connected ? 1 : 0.08, fixedColor: connected ? "var(--success)" : "var(--danger)" },
      ]
    : [];

  return (
    <div className="dash">
      <TopBar
        connected={connected}
        user={user}
        tel={tel}
        liveTimestamp={frame?.telemetry.timestamp}
        eventsPerSecond={eventsPerSecond}
        routeDistanceKm={routeDistanceKm}
        routeDistanceTotalKm={ROUTE_DISTANCE_KM}
        themeMode={themeMode}
        viewMode={viewMode}
        playbackPaused={playbackPaused}
        onEnterLiveMode={enterLiveMode}
        onEnterReplayMode={enterReplayMode}
        onTogglePlaybackPause={togglePlaybackPause}
        onToggleTheme={onToggleTheme}
        onLogout={onLogout}
        exportSummaryHref={exportSummaryUrl()}
        exportCsvHref={exportCsvUrl()}
        exportCsv24hHref={exportCsvRangeUrl(24)}
        exportCsv72hHref={exportCsvRangeUrl(72)}
        timeLabel={timeLabel}
      />

      <Sidebar
        tel={tel}
        alerts={alerts}
        topFactors={topFactors}
        health={health}
        healthTone={healthTone}
        healthValue={healthValue}
        loadMultiplier={loadMultiplier}
        onSend={(action, value) => {
          if (action === "set_load") {
            const next = Number(value);
            if (next === 1 || next === 5 || next === 10) {
              setLoadMultiplier(next);
            }
          }
          send(action, value);
        }}
        timeLabel={timeLabel}
      />

      <div className="main-panel">
        <div className={`fault-banner ${topCriticalAlert ? "show" : ""}`}>
          <span>⛔</span>
          <span>
            {topCriticalAlert
              ? `${FAULT_LABELS[topCriticalAlert.code] ?? topCriticalAlert.title} · индекс: ${Math.round(healthValue)} · статус: ${healthStatusLabel(health?.label)}`
              : "Система в норме"}
          </span>
        </div>

        <div className="kpi-row">
          <KpiCard label="Скорость" value={tel ? tel.speed_kmh.toFixed(1) : "—"} unit="км/ч" sub={STATE_LABELS[tel?.state ?? ""] ?? "—"} state={stateTone(tel?.state)} />
          <KpiCard label="Ток тяги" value={tel ? `${Math.round(tel.current_a)}` : "—"} unit="А" sub={tel ? currentLabel(tel.current_a) : "—"} accent={tel ? currentColor(tel.current_a) : undefined} />
          <KpiCard label="Топливо" value={tel ? tel.fuel_level_pct.toFixed(1) : "—"} unit="%" sub={fuelRate === null ? "—" : `~${fuelRate.toFixed(1)} л/ч`} accent={tel ? fuelColor(tel.fuel_level_pct) : undefined} />
          <KpiCard label="Вибрация" value={tel ? tel.vibration_mm_s.toFixed(2) : "—"} unit="мм/с" sub={tel ? vibrationLabel(tel.vibration_mm_s) : "—"} accent={tel ? vibrationColor(tel.vibration_mm_s) : undefined} />
        </div>

        <ChartsRow
          chartData={chartData}
          viewMode={viewMode}
          replayWindowMinutes={replayWindowMinutes}
          routeDistanceKm={routeDistanceKm}
          routeProgress={routeProgress}
          routePoint={routePoint}
        />

        <LocomotiveSchematic tel={tel} />

        <div className="bottom-row">
          <GaugePanel title="Давление / температуры" gauges={temperatureGauges} />
          <GaugePanel title="Электрика" gauges={electricGauges} />
          <GaugePanel title="Топливо / индекс" gauges={fuelGauges} />
        </div>

        <TrendTimeline
          chartData={chartData}
          latest={latest}
          viewMode={viewMode}
          playbackPaused={playbackPaused}
          replayWindowMinutes={replayWindowMinutes}
          replayFramesLength={replayFrames.length}
          replayStartLabel={replayFrames[0] ? timeLabel(replayFrames[0].telemetry.timestamp) : "—"}
          replayPositionLabel={replayPositionLabel}
          replayMarkers={replayMarkers}
          selectedReplayIndex={selectedReplayIndex}
          onReplayWindowChange={handleReplayWindowChange}
          onReplaySliderChange={handleReplaySliderChange}
        />
      </div>
    </div>
  );
}
