"use client";

import type { GaugeConfig } from "@/utils/dashboard";
import { gaugeTone, gaugeToneInverted } from "@/utils/dashboard";

type GaugePanelProps = {
  title: string;
  gauges: GaugeConfig[];
};

export function GaugePanel({ title, gauges }: GaugePanelProps) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className="gauge-grid">
        {gauges.map((gauge) => {
          const color = gauge.fixedColor ?? (gauge.inverted ? gaugeToneInverted(gauge.fill) : gaugeTone(gauge.fill));
          return (
            <div className="gauge-item" key={gauge.id}>
              <div className="gauge-val">{gauge.value}</div>
              <div className="gauge-bar">
                <div className="gauge-fill" style={{ width: `${gauge.fill * 100}%`, background: color }}></div>
              </div>
              <div className="gauge-lbl">{gauge.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
