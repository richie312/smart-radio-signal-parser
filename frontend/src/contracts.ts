export type ComponentState = 'online' | 'degraded' | 'offline' | 'unconfigured' | 'error';
export type OperatingMode = 'adsb' | 'sdrpp_scanner' | 'aviation_audio';

export interface ComponentStatus {
  state: ComponentState;
  updated_at: string;
  last_success_at: string | null;
  last_message_at?: string | null;
  error_code: string | null;
  details: Record<string, unknown>;
}

export interface SystemStatus {
  operating_mode: OperatingMode;
  api: ComponentStatus;
  database: ComponentStatus;
  receiver: ComponentStatus;
  decoder: ComponentStatus;
  ingestion: ComponentStatus;
  audio: ComponentStatus;
  site: Record<string, unknown>;
}

export interface AircraftObservation {
  observation_id: number | string;
  record_kind: 'decoded_frame' | 'aircraft_update';
  icao24: string;
  receiver_id: string;
  event_time: string | null;
  ingested_at: string;
  source_event_id: string | null;
  callsign: string | null;
  latitude_deg: number | null;
  longitude_deg: number | null;
  altitude_ft: number | null;
  ground_speed_kt: number | null;
  track_deg: number | null;
  vertical_rate_fpm: number | null;
  squawk: string | null;
  on_ground: boolean | null;
  signal_metric: number | null;
  signal_metric_kind: string | null;
  signal_metric_unit: string | null;
  decoder_name: string;
  decoder_version: string | null;
}

export interface EnrichmentResult<T = Record<string, unknown>> {
  state: string;
  provider_id: string | null;
  fetched_at: string | null;
  expires_at: string | null;
  match_confidence: number | null;
  data: T | null;
  attribution: string | null;
  safe_error_code: string | null;
}

export interface AircraftSummary {
  icao24: string;
  first_seen_at: string;
  last_seen_at: string;
  last_observation: AircraftObservation;
  current_session_id: string | null;
  image: EnrichmentResult<{ image_url: string; attribution: string; source_page: string; license: string }>;
  flight_info: EnrichmentResult<{
    flight_id: string;
    origin: string | null;
    destination: string | null;
    provider_time: string | null;
    valid_from: string | null;
    valid_to: string | null;
  }>;
}

export interface Page<T> { items: T[]; next_cursor: string | null }

export interface AnalyticsSummary {
  window: { from: string; to: string };
  receiver_id: string | null;
  data_available: boolean;
  aircraft_count: number;
  message_count: number | null;
  message_rate_per_second: number | null;
  message_metrics_available: boolean;
  aircraft_update_count: number;
  position_update_count: number;
  distance: { minimum_observed_m: number | null; valid_position_count: number };
  signal_metrics: Array<{
    kind: string;
    unit: string;
    calibration_status: string | null;
    aggregation: string;
    value: number | null;
  }>;
  receiver_state: { state: ComponentState; uptime_seconds: number | null; definition: string };
}

export interface TimeseriesBucket {
  bucket_start: string;
  decoded_frame_count: number | null;
  aircraft_update_count: number;
  distinct_aircraft_count: number;
}

export interface AnalyticsTimeseries {
  window: { from: string; to: string };
  bucket_seconds: number;
  receiver_id: string | null;
  data_available: boolean;
  buckets: TimeseriesBucket[];
}

export interface Problem {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
  request_id: string;
}

export interface AudioStation {
  station_id: string;
  name: string;
  frequency_mhz: number | null;
  band: string | null;
  modulation: string | null;
  state: ComponentState;
  playback_url: string | null;
}

export interface AudioConfig {
  state: ComponentState;
  airport: string;
  source: string;
  mode: string | null;
  station_id: string | null;
  stations: AudioStation[];
}
