import type { AnalyticsSummary, AnalyticsTimeseries, AudioConfig, AircraftSummary, SystemStatus } from './contracts';

// These fixtures are accessible only through ?testData=1 and are always labeled in the UI.
const now = new Date();
const stamp = (minutesAgo: number) => new Date(now.getTime() - minutesAgo * 60_000).toISOString();
const component = (state: 'online' | 'unconfigured' = 'online') => ({ state, updated_at: stamp(0), last_success_at: state === 'online' ? stamp(0) : null, error_code: null, details: {} });

export const testStatus: SystemStatus = {
  operating_mode: 'adsb', api: component(), database: component(),
  receiver: { ...component(), last_message_at: stamp(1), details: { mode: 'rtlsdr_usb', owner: 'adsb_decoder', last_message_at: stamp(1), reconnect_attempts: 0 } },
  decoder: { ...component(), last_message_at: stamp(1), details: { name: 'TEST DECODER', version: 'fixture' } },
  ingestion: { ...component(), details: { accepted_count: 1234, rejected_count: 0, last_persisted_at: stamp(1) } },
  audio: component('unconfigured'), site: { receiver_id: 'TEST-ONLY' },
};

export const testAircraft: AircraftSummary[] = [{
  icao24: 'A1B2C3', first_seen_at: stamp(40), last_seen_at: stamp(1), current_session_id: 'TEST-SESSION',
  last_observation: {
    observation_id: 1, record_kind: 'aircraft_update', icao24: 'A1B2C3', receiver_id: 'TEST-ONLY', event_time: stamp(1), ingested_at: stamp(1), source_event_id: null,
    callsign: 'TEST123', latitude_deg: 37.6213, longitude_deg: -122.3790, altitude_ft: 12000, ground_speed_kt: 240, track_deg: 90, vertical_rate_fpm: 0, squawk: null, on_ground: false,
    signal_metric: null, signal_metric_kind: null, signal_metric_unit: null, decoder_name: 'TEST DECODER', decoder_version: 'fixture',
  },
  image: { state: 'unconfigured', provider_id: null, fetched_at: null, expires_at: null, match_confidence: null, data: null, attribution: null, safe_error_code: null },
  flight_info: { state: 'unconfigured', provider_id: null, fetched_at: null, expires_at: null, match_confidence: null, data: null, attribution: null, safe_error_code: null },
}];

export const testSummary: AnalyticsSummary = {
  window: { from: stamp(60), to: stamp(0) }, receiver_id: 'TEST-ONLY', data_available: true, aircraft_count: 1,
  message_count: null, message_rate_per_second: null, message_metrics_available: false, aircraft_update_count: 120, position_update_count: 82,
  distance: { minimum_observed_m: 6240, valid_position_count: 82 }, signal_metrics: [], receiver_state: { state: 'online', uptime_seconds: 3600, definition: 'TEST DATA' },
};

export const testTimeseries: AnalyticsTimeseries = {
  window: { from: stamp(60), to: stamp(0) }, bucket_seconds: 600, receiver_id: 'TEST-ONLY', data_available: true,
  buckets: Array.from({ length: 6 }, (_, i) => ({ bucket_start: stamp((5 - i) * 10), decoded_frame_count: null, aircraft_update_count: 20, distinct_aircraft_count: 1 })),
};

export const testAudio: AudioConfig = { state: 'unconfigured', airport: '', source: '', mode: null, station_id: null, stations: [] };
