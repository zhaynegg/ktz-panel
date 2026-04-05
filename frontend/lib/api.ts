const DEFAULT_API_BASE = "http://localhost:8000";

async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
}

export function apiBase(): string {
  const raw =
    typeof window !== "undefined"
      ? process.env.NEXT_PUBLIC_API_URL?.trim()
      : undefined;
  return (raw && raw.length > 0 ? raw : DEFAULT_API_BASE).replace(/\/$/, "");
}

export function wsBase(): string {
  return apiBase().replace(/^http/, "ws");
}

// --- Types ---

export type TelemetryPoint = {
  timestamp: string;
  state: string;
  speed_kmh: number;
  traction_power_kw: number;
  engine_temp_c: number;
  transformer_temp_c: number;
  brake_pipe_pressure_bar: number;
  voltage_v: number;
  current_a: number;
  vibration_mm_s: number;
  fuel_level_pct: number;
  fault_code: string | null;
  raw_speed_kmh?: number;
  raw_engine_temp_c?: number;
};

export type HealthFactor = {
  parameter: string;
  score: number;
  weight: number;
  detail: string;
};

export type HealthIndex = {
  value: number;
  label: string; // GOOD / WARNING / CRITICAL
  factors: HealthFactor[];
  timestamp: string;
};

export type Alert = {
  id: string;
  ts: string;
  severity: string;
  code: string;
  title: string;
  detail: string | null;
  recommendation: string | null;
  acknowledged: boolean;
};

export type StreamFrame = {
  telemetry: TelemetryPoint;
  health: HealthIndex;
  alerts: Alert[];
};

export type GraphSeries = {
  ticks: number[];
  speed_kmh: number[];
  traction_power_kw: number[];
  engine_temp_c: number[];
  transformer_temp_c: number[];
  brake_pipe_pressure_bar: number[];
  vibration_mm_s: number[];
  health_index: number[];
  states: string[];
};

export type QualityResult = {
  passed: boolean;
  avg_residual: number;
  max_residual: number;
  fault_ticks: number;
  total_ticks: number;
  message: string;
};

export type SimulationResponse = {
  series: GraphSeries;
  quality: QualityResult;
};

export type AiMetricStats = {
  min: number;
  max: number;
  avg: number;
  trend: string;
};

export type AiSummaryResponse = {
  enabled: boolean;
  available: boolean;
  source: string;
  model: string | null;
  generated_at: string;
  window_minutes: number;
  risk_level: string;
  summary: string;
  forecast: string;
  recommendations: string[];
  current_health: number;
  previous_health: number;
  health_delta: number;
  active_alerts_count: number;
  metrics: Record<string, AiMetricStats>;
};

export type UserInfo = {
  username: string;
};

// --- REST calls ---

export async function fetchCurrent(): Promise<StreamFrame> {
  const res = await apiFetch(`${apiBase()}/api/v1/telemetry/current`);
  if (!res.ok) throw new Error("Failed to fetch current telemetry");
  return (await res.json()) as StreamFrame;
}

export async function fetchGraph(lastN = 200): Promise<GraphSeries> {
  const res = await apiFetch(`${apiBase()}/api/v1/telemetry/graph?last_n=${lastN}`);
  if (!res.ok) throw new Error("Failed to fetch graph data");
  return (await res.json()) as GraphSeries;
}

export async function fetchHistory(lastN = 600): Promise<StreamFrame[]> {
  const res = await apiFetch(`${apiBase()}/api/v1/telemetry/history?last_n=${lastN}`);
  if (!res.ok) throw new Error("Failed to fetch telemetry history");
  return (await res.json()) as StreamFrame[];
}

export async function fetchSimulation(
  ticks = 200,
  seed = 42,
  type = "electric"
): Promise<SimulationResponse> {
  const res = await apiFetch(
    `${apiBase()}/api/v1/simulation/run?ticks=${ticks}&seed=${seed}&locomotive_type=${type}`
  );
  if (!res.ok) throw new Error("Failed to run simulation");
  return (await res.json()) as SimulationResponse;
}

export async function fetchAiSummary(): Promise<AiSummaryResponse> {
  const res = await apiFetch(`${apiBase()}/api/v1/analysis/ai-summary`);
  if (!res.ok) throw new Error("Failed to fetch AI summary");
  return (await res.json()) as AiSummaryResponse;
}

export async function fetchAlerts(): Promise<Alert[]> {
  const res = await apiFetch(`${apiBase()}/api/v1/alerts`);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return (await res.json()) as Alert[];
}

export async function acknowledgeAlert(id: string): Promise<void> {
  await apiFetch(`${apiBase()}/api/v1/alerts/${id}/acknowledge`, { method: "POST" });
}

export async function setSimulatorState(state: string): Promise<void> {
  await apiFetch(`${apiBase()}/api/v1/simulator/state?state=${state}`, { method: "POST" });
}

export async function triggerAnomaly(name: string): Promise<void> {
  await apiFetch(`${apiBase()}/api/v1/simulator/anomaly?name=${name}`, { method: "POST" });
}

export function exportCsvUrl(lastN = 500): string {
  return `${apiBase()}/api/v1/telemetry/export/csv?last_n=${lastN}`;
}

export function exportCsvRangeUrl(hours = 24): string {
  return `${apiBase()}/api/v1/telemetry/export/csv/range?hours=${hours}`;
}

export function exportSummaryUrl(): string {
  return `${apiBase()}/api/v1/telemetry/export/summary`;
}

export async function fetchMe(): Promise<UserInfo> {
  const res = await apiFetch(`${apiBase()}/api/v1/auth/me`);
  if (!res.ok) throw new Error("Unauthorized");
  const data = (await res.json()) as { authenticated: boolean; user: UserInfo };
  return data.user;
}

export async function login(username: string, password: string): Promise<UserInfo> {
  const res = await apiFetch(`${apiBase()}/api/v1/auth/login`, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = (await res.json()) as { ok: boolean; user: UserInfo };
  return data.user;
}

export async function logout(): Promise<void> {
  await apiFetch(`${apiBase()}/api/v1/auth/logout`, {
    method: "POST",
  });
}
