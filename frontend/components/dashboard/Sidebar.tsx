"use client";

import type { Alert, HealthFactor, HealthIndex, TelemetryPoint } from "@/lib/api";
import {
  FACTOR_LABELS,
  STATE_LABELS,
  alertDotClass,
  clamp01,
  healthBadgeClass,
  healthStatusLabel,
  riskTone,
} from "@/utils/dashboard";

export function Sidebar({
  tel,
  alerts,
  topFactors,
  health,
  healthTone,
  healthValue,
  loadMultiplier,
  onSend,
  timeLabel,
}: {
  tel?: TelemetryPoint;
  alerts: Alert[];
  topFactors: HealthFactor[];
  health?: HealthIndex;
  healthTone: string;
  healthValue: number;
  loadMultiplier: 1 | 5 | 10;
  onSend: (action: string, value: string) => void;
  timeLabel: (value: string) => string;
}) {
  return (
    <div className="sidebar">
      <div className="card">
        <div className="card-title">Индекс здоровья</div>
        <div className="health-ring-wrap">
          <svg width="130" height="74" viewBox="0 0 130 74" aria-hidden="true">
            <path d="M 12 70 A 53 53 0 0 1 118 70" fill="none" stroke="var(--route-track)" strokeWidth="9" strokeLinecap="round" />
            <path
              d="M 12 70 A 53 53 0 0 1 118 70"
              fill="none"
              stroke={healthTone}
              strokeWidth="9"
              strokeLinecap="round"
              strokeDasharray="166"
              strokeDashoffset={166 - (healthValue / 100) * 166}
              style={{ transition: "stroke-dashoffset 0.6s, stroke 0.6s" }}
            />
            <text x="65" y="65" textAnchor="middle" fontSize="10" fill="var(--text-soft)">
              0 · · · 100
            </text>
          </svg>
          <div className="health-score" style={{ color: healthTone }}>
            {health ? Math.round(health.value) : "—"}
          </div>
          <div className={`health-status-badge ${healthBadgeClass(health?.label)}`}>
            {healthStatusLabel(health?.label)}
          </div>
        </div>

        <div className="card-title spacer-title">Топ факторы риска</div>
        <div className="health-factors">
          {topFactors.length > 0 ? (
            topFactors.map((factor) => {
              const fill = clamp01(1 - factor.score / 100);
              const color = riskTone(fill);
              return (
                <div className="factor" key={factor.parameter}>
                  <div className="factor-name">{FACTOR_LABELS[factor.parameter] ?? factor.parameter}</div>
                  <div className="factor-bar-wrap">
                    <div className="factor-bar" style={{ width: `${Math.max(fill * 100, 8)}%`, background: color }}></div>
                  </div>
                  <div className="factor-val" style={{ color }}>
                    {(100 - factor.score).toFixed(0)}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="empty-copy">Все параметры в норме</div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          Алерты {alerts.length ? <span className="muted-inline">· {alerts.length} активных</span> : null}
        </div>
        <div className="alert-list">
          {alerts.length > 0 ? (
            alerts.slice(0, 6).map((alert) => (
              <div className="alert-item" key={alert.id}>
                <div className={`alert-dot ${alertDotClass(alert.severity)}`}></div>
                <div>
                  <div className="alert-text">{alert.title}</div>
                  {alert.detail ? <div className="alert-detail">{alert.detail}</div> : null}
                  <div className="alert-time">{timeLabel(alert.ts)}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="no-alerts">Нет активных алертов</div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-title">Состояние симулятора</div>
        <div className="state-btns">
          {["IDLE", "CRUISING", "ACCELERATING", "BRAKING"].map((state) => (
            <button
              key={state}
              className={`state-btn ${tel?.state === state ? "active" : ""}`}
              type="button"
              onClick={() => onSend("set_state", state)}
            >
              {STATE_LABELS[state]}
            </button>
          ))}
        </div>

        <div className="card-title spacer-title">
          Нагрузка потока <span className="muted-inline">· {loadMultiplier}x</span>
        </div>
        <div className="state-btns section-actions">
          {[1, 5, 10].map((multiplier) => (
            <button
              key={multiplier}
              className={`state-btn ${loadMultiplier === multiplier ? "active" : ""}`}
              type="button"
              onClick={() => onSend("set_load", String(multiplier))}
            >
              {multiplier}x
            </button>
          ))}
        </div>

        <div className="card-title spacer-title">Инжектировать аномалию</div>
        <div className="anomaly-btns section-actions">
          <button className="anomaly-btn" type="button" onClick={() => onSend("trigger_anomaly", "OVERHEAT")}>
            Перегрев
          </button>
          <button className="anomaly-btn" type="button" onClick={() => onSend("trigger_anomaly", "BRAKE_PRESSURE_DROP")}>
            Давление тормоза
          </button>
          <button className="anomaly-btn" type="button" onClick={() => onSend("trigger_anomaly", "HIGH_VIBRATION")}>
            Вибрация
          </button>
          <button className="anomaly-btn" type="button" onClick={() => onSend("trigger_anomaly", "VOLTAGE_SAG")}>
            Просадка напряжения
          </button>
          <button className="anomaly-btn" type="button" onClick={() => onSend("trigger_anomaly", "OVERCURRENT_SPIKE")}>
            Бросок тока
          </button>
          <button className="anomaly-btn" type="button" onClick={() => onSend("trigger_anomaly", "FUEL_LEAK")}>
            Утечка топлива
          </button>
        </div>

        <div className="card-title spacer-title">Сервисные действия</div>
        <div className="state-btns section-actions">
          <button className="state-btn" type="button" onClick={() => onSend("refuel_full", "")}>
            Заправить до 100%
          </button>
        </div>
      </div>
    </div>
  );
}
