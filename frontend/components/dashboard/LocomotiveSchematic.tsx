"use client";

import type { TelemetryPoint } from "@/lib/api";
import { metricState, type ZoneState, zoneStateLabel, zoneTone, worstZoneState } from "@/utils/dashboard";

function zoneFill(state: ZoneState) {
  return `color-mix(in srgb, ${zoneTone(state)} 22%, transparent)`;
}

export function LocomotiveSchematic({ tel }: { tel?: TelemetryPoint }) {
  if (!tel) {
    return (
      <div className="chart-card loco-card">
        <div className="section-header">
          <span className="card-title section-title">Схема локомотива</span>
          <span className="route-tick">Нет данных</span>
        </div>
        <div className="empty-copy">Схема появится после первого telemetry frame.</div>
      </div>
    );
  }

  const engineState = metricState(tel.engine_temp_c, 85, 95, true);
  const coolingState = metricState(tel.transformer_temp_c, 80, 92, true);
  const brakeState = metricState(tel.brake_pipe_pressure_bar, 4.3, 3.5, false);
  const fuelState = metricState(tel.fuel_level_pct, 20, 10, false);
  const bogieState = metricState(tel.vibration_mm_s, 1.8, 2.5, true);
  const electricState = worstZoneState([
    metricState(tel.current_a, 700, 850, true),
    metricState(tel.voltage_v, 24300, 24050, false),
  ]);

  const zones = [
    { id: "engine", label: "Двигатель", value: `${tel.engine_temp_c.toFixed(1)} °C`, state: engineState },
    { id: "cooling", label: "Охлаждение", value: `${tel.transformer_temp_c.toFixed(1)} °C`, state: coolingState },
    { id: "electric", label: "Силовая часть", value: `${Math.round(tel.current_a)} А / ${Math.round(tel.voltage_v)} В`, state: electricState },
    { id: "brake", label: "Тормоза", value: `${tel.brake_pipe_pressure_bar.toFixed(2)} бар`, state: brakeState },
    { id: "fuel", label: "Топливный бак", value: `${tel.fuel_level_pct.toFixed(1)} %`, state: fuelState },
    { id: "bogies", label: "Тележки", value: `${tel.vibration_mm_s.toFixed(2)} мм/с`, state: bogieState },
  ] as const;

  return (
    <div className="chart-card loco-card">
      <div className="section-header">
        <span className="card-title section-title">Схема локомотива</span>
        <span className="route-tick">Диагностика по узлам</span>
      </div>

      <div className="loco-layout">
        <div className="loco-illustration-wrap">
          <svg className="loco-svg" viewBox="0 0 360 170" aria-label="Схема дизельного локомотива">
            <rect x="34" y="56" width="242" height="64" rx="14" fill="var(--surface-soft)" stroke="var(--border-strong)" />
            <rect x="98" y="34" width="106" height="44" rx="12" fill="var(--surface-soft)" stroke="var(--border-strong)" />
            <rect x="274" y="68" width="48" height="52" rx="10" fill="var(--surface-soft)" stroke="var(--border-strong)" />
            <path d="M 40 120 L 324 120" stroke="var(--border-strong)" strokeWidth="3" strokeLinecap="round" />
            <circle cx="92" cy="134" r="18" fill="var(--surface-soft)" stroke="var(--border-strong)" strokeWidth="3" />
            <circle cx="92" cy="134" r="8" fill="var(--route-track)" />
            <circle cx="262" cy="134" r="18" fill="var(--surface-soft)" stroke="var(--border-strong)" strokeWidth="3" />
            <circle cx="262" cy="134" r="8" fill="var(--route-track)" />

            <rect x="52" y="67" width="72" height="40" rx="10" fill={zoneFill(engineState)} stroke={zoneTone(engineState)} strokeWidth="2" />
            <rect x="132" y="67" width="56" height="40" rx="10" fill={zoneFill(coolingState)} stroke={zoneTone(coolingState)} strokeWidth="2" />
            <rect x="194" y="67" width="56" height="40" rx="10" fill={zoneFill(electricState)} stroke={zoneTone(electricState)} strokeWidth="2" />
            <rect x="258" y="76" width="52" height="32" rx="10" fill={zoneFill(brakeState)} stroke={zoneTone(brakeState)} strokeWidth="2" />
            <rect x="36" y="109" width="84" height="16" rx="8" fill={zoneFill(fuelState)} stroke={zoneTone(fuelState)} strokeWidth="2" />
            <circle cx="92" cy="134" r="22" fill={zoneFill(bogieState)} stroke={zoneTone(bogieState)} strokeWidth="2" />
            <circle cx="262" cy="134" r="22" fill={zoneFill(bogieState)} stroke={zoneTone(bogieState)} strokeWidth="2" />

            <text x="88" y="89" textAnchor="middle" className="loco-zone-text">Двиг.</text>
            <text x="160" y="89" textAnchor="middle" className="loco-zone-text">Охлажд.</text>
            <text x="222" y="89" textAnchor="middle" className="loco-zone-text">Эл.</text>
            <text x="284" y="96" textAnchor="middle" className="loco-zone-text">Торм.</text>
            <text x="78" y="121" textAnchor="middle" className="loco-zone-text">Бак</text>
          </svg>
        </div>

        <div className="loco-legend">
          {zones.map((zone) => (
            <div className="loco-metric" key={zone.id}>
              <div className="loco-metric-top">
                <span className="loco-metric-label">
                  <span className="loco-dot-indicator" style={{ background: zoneTone(zone.state) }}></span>
                  {zone.label}
                </span>
                <span className="loco-metric-status" style={{ color: zoneTone(zone.state) }}>
                  {zoneStateLabel(zone.state)}
                </span>
              </div>
              <div className="loco-metric-value">{zone.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
