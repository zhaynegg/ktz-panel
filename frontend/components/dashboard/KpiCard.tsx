"use client";

type KpiCardProps = {
  label: string;
  value: string;
  unit: string;
  sub: string;
  accent?: string;
  state?: { text: string; className: string };
};

export function KpiCard({ label, value, unit, sub, accent, state }: KpiCardProps) {
  return (
    <div className="kpi">
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val" style={accent ? { color: accent } : undefined}>
        {value}
        <span className="kpi-unit"> {unit}</span>
      </div>
      {state ? (
        <div>
          <span className={`kpi-state ${state.className}`}>{state.text}</span>
        </div>
      ) : null}
      <div className="kpi-sub">{sub}</div>
    </div>
  );
}
