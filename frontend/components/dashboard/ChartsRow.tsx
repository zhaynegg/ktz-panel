"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartPoint } from "@/utils/dashboard";
import { ROUTE_DISTANCE_KM, ROUTE_LENGTH, ROUTE_PATH, tooltipStyle } from "@/utils/dashboard";

export function ChartsRow({
  chartData,
  viewMode,
  replayWindowMinutes,
  routeDistanceKm,
  routeProgress,
  routePoint,
}: {
  chartData: ChartPoint[];
  viewMode: "live" | "replay";
  replayWindowMinutes: number;
  routeDistanceKm: number;
  routeProgress: number;
  routePoint: { x: number; y: number };
}) {
  return (
    <div className="charts-row">
      <div className="chart-card">
        <div className="section-header">
          <span className="card-title section-title">Температуры / тормозное давление</span>
          <div className="live-badge">
            <div className="live-dot"></div>
            {viewMode === "live" ? "LIVE 1 Гц" : `REPLAY · ${replayWindowMinutes} мин`}
          </div>
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={chartData}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "var(--text-soft)" }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="temp" domain={[40, 110]} tick={{ fontSize: 10, fill: "var(--warning-strong)" }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="brake" orientation="right" domain={[2.5, 5.4]} tick={{ fontSize: 10, fill: "var(--info-strong)" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line yAxisId="temp" type="monotone" dataKey="engineTemp" name="Темп. двиг." stroke="var(--warning-strong)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="temp" type="monotone" dataKey="transformerTemp" name="Темп. трансф." stroke="var(--danger-strong)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line yAxisId="brake" type="monotone" dataKey="brakePressure" name="Давл. тормоза" stroke="var(--info-strong)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-card">
        <div className="section-header">
          <span className="card-title section-title">Маршрут</span>
          <span className="route-tick">{routeDistanceKm}/{ROUTE_DISTANCE_KM} км</span>
        </div>
        <svg className="route-svg" viewBox="0 0 220 130">
          <path d={ROUTE_PATH} fill="none" stroke="var(--route-track)" strokeWidth="3" strokeLinecap="round" />
          <path
            d={ROUTE_PATH}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${ROUTE_LENGTH * routeProgress} ${Math.max(ROUTE_LENGTH * (1 - routeProgress), 0.01)}`}
          />
          <circle cx="20" cy="115" r="5" fill="var(--accent)" />
          <text x="6" y="128" fontSize="8" fill="var(--text-muted)">Алматы</text>
          <circle cx={routePoint.x} cy={routePoint.y} r="5" fill="var(--info-strong)" stroke="var(--surface-raised)" strokeWidth="2" />
          <text x={routePoint.x + 3} y={routePoint.y - 4} fontSize="8" fill="var(--accent)">● здесь</text>
          <circle cx="200" cy="40" r="4" fill="var(--route-track)" />
          <text x="183" y="36" fontSize="8" fill="var(--text-muted)">Астана</text>
          <rect x="115" y="59" width="14" height="9" rx="2" fill="var(--warning-soft)" />
          <text x="122" y="66" textAnchor="middle" fontSize="7" fill="var(--warning)">1000</text>
        </svg>
      </div>
    </div>
  );
}
