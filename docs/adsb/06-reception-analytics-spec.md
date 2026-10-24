# ADS-B Application: Reception Analytics

> **Finalized contract note:** Analytics endpoint query names and response semantics are in [12](12-shared-contracts-and-configuration.md). Event-time versus ingestion-time and measured versus calculated values must retain the distinctions below and in the shared contract.

## Metric definitions

All analytics responses include a UTC time window, bucket width where applicable, receiver scope, and whether values are observed or calculated.

### Directly observed or decoded

- **Aircraft observed**: distinct ICAO24 values with at least one accepted observation in the window.
- **Decoded frame count/rate**: count only envelopes with `record_kind=decoded_frame`, using `ingested_at` for operational rate. If the decoder emits only aggregated `aircraft_update` records, frame count/rate are unavailable (`null` plus an availability flag), not a count of snapshots mislabeled as radio messages.
- **Aircraft update count**: count accepted aggregated state-update records when that is the decoder output kind. Keep separate from decoded-frame count.
- **Position updates**: count of accepted observations containing valid position.
- **Signal metric**: only when receiver/decoder genuinely emits it; include its kind, units, sample/aggregation method and calibrated status. Do not label arbitrary decoder signal values as calibrated RSSI/SNR.
- **Receiver uptime/state**: derived from state transitions and heartbeat/message freshness; report definition and gaps.

### Calculated

- **Coverage by range**: count/percentage of aircraft observations whose valid position is within configured distance bands from receiver during window. Distance is geometric great-circle distance, not radio coverage boundary.
- **Minimum observed distance**: min from valid observed positions; sparse sampling caveat.
- **Timeseries aggregates**: bucketed counts/rates over selected intervals.
- **Reception spread**: optional range/altitude distributions from observed data only.

## API expectations

See `/api/v1/analytics/summary` and `/timeseries` in [02](02-backend-spec.md). Bound max window, bucket count, and page size. Empty data returns zeros/empty arrays with `data_available: false`, not a fabricated baseline. Use UTC half-open intervals `[from, to)` to avoid double counting at adjacent boundaries.

## Aggregation and performance

Initially query indexed observation tables with explicit time bounds. Add pre-aggregated rollups only when measured workload requires them; document refresh delay and source if introduced. Use consistent receiver filters and avoid counting one aircraft multiple times within a distinct-aircraft metric. Preserve metric definitions across UI labels and API docs.

## Cross references

Signal field validity is specified in [03](03-receiver-and-decoder-spec.md); persistence indexes in [04](04-mysql-data-model.md); presentation in [08](08-react-frontend-spec.md).
