import type { AnalyticsSummary, AnalyticsTimeseries, AudioConfig, AircraftSummary, ComponentStatus, Page, Problem, SystemStatus } from './contracts';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, readonly code = 'network_error', readonly requestId: string | null = null) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' }, signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('The API could not be reached. Check the connection and retry.');
  }
  const body = await response.json().catch(() => null) as T | Problem | null;
  if (!response.ok) {
    const problem = body as Problem | null;
    throw new ApiError(problem?.message ?? `Request failed (${response.status}).`, problem?.code ?? 'http_error', problem?.request_id ?? null);
  }
  return body as T;
}

export const api = {
  status: (signal?: AbortSignal) => request<SystemStatus>('/api/v1/status', signal),
  aircraft: (params: URLSearchParams, signal?: AbortSignal) => request<Page<AircraftSummary>>(`/api/v1/aircraft?${params}`, signal),
  summary: (from: string, to: string, signal?: AbortSignal) => request<AnalyticsSummary>(`/api/v1/analytics/summary?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`, signal),
  timeseries: (from: string, to: string, bucketSeconds: number, signal?: AbortSignal) => request<AnalyticsTimeseries>(`/api/v1/analytics/timeseries?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&bucket_seconds=${bucketSeconds}`, signal),
  audio: (signal?: AbortSignal) => request<AudioConfig>('/api/v1/audio/config', signal),
  startAudio: async (stationId: string) => {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}/api/v1/audio/start`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ station_id: stationId }),
      });
    } catch { throw new ApiError('The API could not be reached. Check the connection and retry.'); }
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const problem = body as Problem | null;
      throw new ApiError(problem?.message ?? `Request failed (${response.status}).`, problem?.code ?? 'http_error', problem?.request_id ?? null);
    }
    return body as { mode: string; station_id: string; playback_url: string };
  },
  stopAudio: async () => {
    let response: Response;
    try { response = await fetch(`${API_BASE}/api/v1/audio/stop`, { method: 'POST', headers: { Accept: 'application/json' } }); }
    catch { throw new ApiError('The API could not be reached. Check the connection and retry.'); }
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const problem = body as Problem | null;
      throw new ApiError(problem?.message ?? `Request failed (${response.status}).`, problem?.code ?? 'http_error', problem?.request_id ?? null);
    }
    return body as { mode: string; station_id: null };
  },
};

export function classifyReception(status: SystemStatus | null): { label: string; state: ComponentStatus['state']; lastMessage: string | null } {
  if (!status) return { label: 'Waiting for status', state: 'offline', lastMessage: null };
  if (status.operating_mode === 'aviation_audio') return { label: 'ADS-B paused · airband audio owns receiver', state: 'unconfigured', lastMessage: status.receiver.last_message_at ?? null };
  if (status.operating_mode === 'sdrpp_scanner') return { label: 'ADS-B paused · scanner owns receiver', state: 'unconfigured', lastMessage: status.receiver.last_message_at ?? null };
  return { label: `ADS-B ${status.receiver.state}`, state: status.receiver.state, lastMessage: status.receiver.last_message_at ?? status.decoder.last_message_at ?? null };
}

export function makeTimeWindow(hours: number): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to.getTime() - hours * 60 * 60 * 1000);
  return { from: from.toISOString(), to: to.toISOString() };
}

