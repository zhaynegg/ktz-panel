"use client";

import type { Alert, StreamFrame } from "@/lib/api";

export const MAX_POINTS = 60;
export const ROUTE_DISTANCE_KM = 1000;
export const ROUTE_PATH = "M 20 115 Q 50 95 80 78 Q 110 62 145 52 Q 175 44 200 40";
export const ROUTE_LENGTH = 203;
export const REPLAY_WINDOWS = [5, 10, 15] as const;
export const REPLAY_DEFAULT_LAG_FRAMES = 10;

export const STATE_LABELS: Record<string, string> = {
  IDLE: "Стоп",
  CRUISING: "Крейсер",
  ACCELERATING: "Разгон",
  BRAKING: "Торможение",
};

export const FAULT_LABELS: Record<string, string> = {
  OVERHEAT: "Перегрев двигателя / трансформатора",
  BRAKE_PRESSURE_DROP: "Падение давления тормозной магистрали",
  HIGH_VIBRATION: "Критическая вибрация корпуса",
  VOLTAGE_SAG: "Просадка напряжения тяговой сети",
  OVERCURRENT_SPIKE: "Бросок тока в силовой цепи",
  FUEL_LEAK: "Утечка топлива",
};

export const FACTOR_LABELS: Record<string, string> = {
  speed_kmh: "Скорость",
  traction_power_kw: "Тяговая мощность",
  engine_temp_c: "Темп. двиг.",
  transformer_temp_c: "Темп. трансф.",
  brake_pipe_pressure_bar: "Давл. тормоза",
  voltage_v: "Напряжение",
  current_a: "Ток тяги",
  vibration_mm_s: "Вибрация",
  fuel_level_pct: "Топливо",
  fault_code: "Код ошибки",
};

export type ChartPoint = {
  time: string;
  speed: number;
  current: number;
  engineTemp: number;
  transformerTemp: number;
  brakePressure: number;
  health: number;
};

export type GaugeConfig = {
  id: string;
  label: string;
  value: string;
  fill: number;
  inverted?: boolean;
  fixedColor?: string;
};

export const tooltipStyle = {
  background: "var(--surface-raised)",
  border: "1px solid var(--border-strong)",
  borderRadius: "10px",
  fontSize: "12px",
  color: "var(--text)",
};

export function healthColor(value: number, label?: string): string {
  if (label === "CRITICAL" || value < 50) return "var(--danger)";
  if (label === "WARNING" || value < 80) return "var(--warning)";
  return "var(--success)";
}

export function healthBadgeClass(label?: string): string {
  if (label === "CRITICAL") return "badge-critical";
  if (label === "WARNING") return "badge-warning";
  return "badge-normal";
}

export function healthStatusLabel(label?: string): string {
  if (label === "CRITICAL") return "Критично";
  if (label === "WARNING") return "Внимание";
  if (label === "GOOD") return "Норма";
  return "—";
}

export function riskTone(value: number): string {
  if (value >= 0.55) return "var(--danger-strong)";
  if (value >= 0.25) return "var(--warning-strong)";
  return "var(--success)";
}

export function gaugeTone(value: number): string {
  if (value < 0.5) return "var(--success)";
  if (value < 0.8) return "var(--warning-strong)";
  return "var(--danger-strong)";
}

export function gaugeToneInverted(value: number): string {
  if (value > 0.6) return "var(--success)";
  if (value > 0.3) return "var(--warning-strong)";
  return "var(--danger-strong)";
}

export function currentColor(value: number): string {
  if (value > 700) return "var(--danger)";
  if (value > 550) return "var(--warning)";
  return "var(--text)";
}

export function currentLabel(value: number): string {
  if (value > 700) return "Высокий";
  if (value > 550) return "Внимание";
  return "Норма";
}

export function fuelColor(value: number): string {
  if (value < 20) return "var(--danger)";
  if (value < 40) return "var(--warning)";
  return "var(--text)";
}

export function vibrationColor(value: number): string {
  if (value > 2) return "var(--danger)";
  if (value > 1.2) return "var(--warning)";
  return "var(--text)";
}

export function vibrationLabel(value: number): string {
  if (value > 2) return "Критично";
  if (value > 1.2) return "Внимание";
  return "Норма";
}

export function stateTone(state?: string): { text: string; className: string } {
  const current = state ?? "IDLE";
  return {
    text: STATE_LABELS[current] ?? current,
    className: `state-${current.toLowerCase()}`,
  };
}

export function alertDotClass(severity: string): string {
  if (severity === "critical") return "dot-danger";
  if (severity === "warning") return "dot-warn";
  return "dot-info";
}

export function highestSeverity(alerts: Alert[]): "critical" | "warning" | "info" {
  if (alerts.some((alert) => alert.severity === "critical")) return "critical";
  if (alerts.some((alert) => alert.severity === "warning")) return "warning";
  return "info";
}

export function timeLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function computeFuelRate(history: StreamFrame[]): number | null {
  if (history.length < 2) return null;
  const first = history[0]?.telemetry;
  const last = history[history.length - 1]?.telemetry;
  if (!first || !last) return null;

  const start = new Date(first.timestamp).getTime();
  const end = new Date(last.timestamp).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null;

  const hours = (end - start) / 3600000;
  if (hours <= 0) return null;

  const consumedPct = first.fuel_level_pct - last.fuel_level_pct;
  return consumedPct > 0 ? (consumedPct / 100) * 6000 / hours : 0;
}

export function computeRouteDistanceKm(history: StreamFrame[], totalDistanceKm = ROUTE_DISTANCE_KM): number {
  if (history.length < 2) return 0;

  let distanceKm = 0;
  for (let index = 1; index < history.length; index += 1) {
    const previous = history[index - 1]?.telemetry;
    const current = history[index]?.telemetry;
    if (!previous || !current) continue;

    const start = new Date(previous.timestamp).getTime();
    const end = new Date(current.timestamp).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) continue;

    const hours = (end - start) / 3600000;
    const averageSpeed = (previous.speed_kmh + current.speed_kmh) / 2;
    distanceKm += averageSpeed * hours;
  }

  return Math.min(distanceKm, totalDistanceKm);
}

export function round(value: number, digits: number): number {
  return Number(value.toFixed(digits));
}

export function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function routePointAt(progress: number): { x: number; y: number } {
  const t = clamp01(progress);
  return {
    x: 20 + 180 * t,
    y: 115 - 75 * Math.pow(t, 0.82),
  };
}

export type ZoneState = "normal" | "warning" | "critical";

export function metricState(value: number, warn: number, crit: number, higherIsWorse = true): ZoneState {
  if (higherIsWorse) {
    if (value >= crit) return "critical";
    if (value >= warn) return "warning";
    return "normal";
  }

  if (value <= crit) return "critical";
  if (value <= warn) return "warning";
  return "normal";
}

export function worstZoneState(states: ZoneState[]): ZoneState {
  if (states.includes("critical")) return "critical";
  if (states.includes("warning")) return "warning";
  return "normal";
}

export function zoneTone(state: ZoneState): string {
  if (state === "critical") return "var(--danger-strong)";
  if (state === "warning") return "var(--warning-strong)";
  return "var(--success)";
}

export function zoneStateLabel(state: ZoneState): string {
  if (state === "critical") return "Критично";
  if (state === "warning") return "Внимание";
  return "Норма";
}
