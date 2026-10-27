# ADS-B Batch 1: Shared Contracts and Canonical Configuration

This document is authoritative where an earlier illustrative schema, route, state, or variable list conflicts. Implementation must retain these field meanings. Optional provider/audio fields remain unavailable until configured.

## Operating mode and status

`OPERATING_MODE` is exactly `adsb` or `sdrpp_scanner`. One owner only. Switching requires stop active process, confirm USB release, start target, verify ownership/output, then report status. Never auto-take over. ADS-B mode owns the RTL-SDR for decoder use; scanner mode reserves it for existing SDR++ workflow and ADS-B ingestion is inactive by mode. Preserve existing Python scripts.

Component states are `online`, `degraded`, `offline`, `unconfigured`, or `error`. `last_success_at`, `last_message_at`, and error fields may be null; do not use zero timestamps/counters to mean unknown. Scanner mode reports ADS-B receiver/decoder as `unconfigured` with reason `inactive_by_mode`. API readiness requires API startup, DB connectivity and compatible schema. Receiver/decoder loss degrades reception but does not make API unready. DB/schema failure makes readiness false; optional provider/audio failure does not.

State meanings: `online` = configured component operating and recent expected work succeeds; `degraded` = component is reachable but stale/no data or partial work failure; `offline` = configured component cannot currently be reached or has stopped; `unconfigured` = capability is not selected/provisioned (including ADS-B disabled by scanner mode); `error` = invalid configuration, ownership conflict, incompatible protocol/schema, or non-recoverable fault. Transition timestamps and safe error codes are retained.

Public status base shape is `{state,updated_at,last_success_at|null,error_code|null,details}`. `receiver.details` includes `mode`, `owner` (`adsb_decoder|sdrpp_scanner|none`), `last_message_at|null`, and `reconnect_attempts`; `decoder.details` includes `name|null`, `version|null`, and `last_message_at|null`; `ingestion.details` includes accepted/rejected counts and last persisted time. In scanner mode, `owner=sdrpp_scanner`, ADS-B receiver/decoder are `unconfigured`, and ingestion is `unconfigured`/inactive by mode. In ADS-B mode before ownership/decoder startup, report `connecting` only internally and public `degraded` or `error`; do not add undocumented public states.

## Decoder path and acceptance evidence

`rtl_tcp` on TCP 1234 (host network in current Compose) supplies receiver control/IQ data, not decoded ADS-B. The selected software candidate is a pinned `readsb` build with RTL-SDR support and direct exclusive USB ownership; its JSON position output is `readsb_json` and represents aggregated aircraft updates (`record_kind=aircraft_update`), not every decoded RF frame. Exact build, listener configuration, line schema, and hardware compatibility remain untested. Do not claim the direct USB path is operational until a real integration test proves device acquisition, correct ADS-B tuning, decoded output, and USB release. No `readsb`-to-current-`rtl_tcp` bridge is assumed. Any proposed bridge needs authoritative protocol/build evidence and its own executable integration test before adapter implementation. Airspy SPY Server/client/version and IQ mode require separate compatibility validation; [Airspy docs](https://airspy.com/quickstart/) alone do not prove chosen decoder interoperability.

## Normalized decoder envelope v1

```json
{
  "schema_version": 1,
  "record_kind": "decoded_frame or aircraft_update",
  "source_event_id": "string or null",
  "event_time": "RFC3339 UTC or null",
  "receiver_id": "stable configured id",
  "decoder": {"name": "string", "version": "string or null"},
  "message": {
    "icao24": "six uppercase hexadecimal characters",
    "callsign": "string or null",
    "latitude_deg": null,
    "longitude_deg": null,
    "altitude_ft": null,
    "ground_speed_kt": null,
    "track_deg": null,
    "vertical_rate_fpm": null,
    "squawk": null,
    "on_ground": null,
    "signal_metric": null,
    "signal_metric_kind": null,
    "signal_metric_unit": null,
    "metadata": {}
  }
}
```

Backend adds `ingested_at` (UTC when accepted) and `observation_id`; never overwrite source `event_time`. All positions/measurements are nullable. `null`=not reported/unknown; zero is numeric zero; invalid input is rejected or normalized to null with reason/counter, never coerced to zero. Signal fields are receiver/decoder-reported measurements only, with kind/unit/calibration semantics; calculated distance/rates are separate.

## Observation and session model

Each envelope represents one decoder output record; `record_kind` is `decoded_frame` when it is a distinct decoded Mode S/ADS-B frame, or `aircraft_update` when the decoder emits an aggregated aircraft state update. The readsb JSON adapter maps one position line to `aircraft_update`; verify its exact installed-build output and live persistence before production acceptance. `AircraftObservation` API and DB fields: `observation_id`, `record_kind`, `icao24`, `receiver_id`, `event_time|null`, `ingested_at`, `source_event_id|null`, `callsign|null`, `latitude_deg|null`, `longitude_deg|null`, `altitude_ft|null`, `ground_speed_kt|null`, `track_deg|null`, `vertical_rate_fpm|null`, `squawk|null`, `on_ground|null`, `signal_metric|null`, `signal_metric_kind|null`, `signal_metric_unit|null`, `decoder_name`, `decoder_version|null`.

Table `aircraft` is keyed by ICAO24. `aircraft_observations` references aircraft and receiver. Required indexes: unique `(receiver_id, decoder_name, source_event_id)` for non-null event IDs; `(icao24,event_time,observation_id)`, `(receiver_id,ingested_at)`, and `(ingested_at)`. MySQL nullable unique behavior must be verified against configured version. Never deduplicate identical field values when source has no stable event identity; no event ID means insert as a new observation.

`flight_sessions` key is session ID; references aircraft, receiver, first/last observation; fields `started_at`, `last_observed_at`, nullable `ended_at`, observed callsign, minimum calculated distance and source observation. Sessionization is per `(receiver_id,icao24)`. Use `event_time` as session time when supplied, otherwise `ingested_at`; preserve nullable source event time in the observation. Create on first observation. Close when gap exceeds configured `FLIGHT_SESSION_SILENCE_SECONDS`, setting end to last effective observation time. Callsign change alone does not start a session. Late event older than open session start or a closed session is stored as an observation but does not silently reopen/rewrite a session; association may be null. Session interval is required configuration; no duration chosen. Retention is required before production; no duration chosen; explicit unlimited requires owner approval.

## REST contract v1

All times are RFC3339 UTC, all JSON. Cursor pagination uses `limit` (default 50, max 200) and opaque `cursor`, response `{items:[...], next_cursor:string|null}`. Aircraft list sorts newest `last_seen_at` first, then ICAO24 ascending for stable ties. `seen_since`, `from`, and `to` are RFC3339 UTC; observation windows use event time and half-open `[from,to)`. Bounds/window restrictions are implementation-enforced and published in OpenAPI.

| Endpoint | Query | Response |
|---|---|---|
| `GET /health/live` | none | `200 {state:"online"}` if process responds; no dependencies checked. |
| `GET /health/ready` | none | `200` if API+DB/schema ready; otherwise `503 Problem` with component states. Receiver state does not gate readiness. |
| `GET /api/v1/status` | none | `{operating_mode,api,database,receiver,decoder,ingestion,audio,site}`; each component includes state, updated_at, last_success_at|null, last_message_at|null where applicable, error_code|null, safe details. |
| `GET /api/v1/aircraft` | `callsign,icao24,altitude_min_ft,altitude_max_ft,seen_since,limit,cursor` | page of `AircraftSummary`. |
| `GET /api/v1/aircraft/{icao24}` | 6-hex path | one `AircraftSummary`; 404 if unknown. |
| `GET /api/v1/aircraft/{icao24}/observations` | `from,to,limit,cursor` | observation page, event time then ID order; `[from,to)`. |
| `GET /api/v1/aircraft/{icao24}/sessions` | `from,to,limit,cursor` | session page. |
| `GET /api/v1/analytics/summary` | `from,to,receiver_id?` | counts, rates, valid-position count, distance summary, available signal metric list, status/availability. |
| `GET /api/v1/analytics/timeseries` | `from,to,bucket_seconds,receiver_id?` | `{window:{from,to},bucket_seconds,receiver_id|null,data_available,buckets:[{bucket_start,decoded_frame_count|null,aircraft_update_count,distinct_aircraft_count}]}`; bucket starts are UTC, intervals are half-open, and frame counts are null when unavailable. |
| `GET /api/v1/enrichment/{icao24}` | none | image and flight `EnrichmentResult`; provider failures represented as states. |
| `GET /api/v1/audio/config` | none | `{state,stations:[{station_id,name,frequency_mhz|null,band|null,modulation|null,state,playback_url|null}]}`; playback URL exists only for a verified configured source. |

Filter semantics: `icao24` is case-insensitive input normalized to uppercase; callsign filtering trims padding and compares case-insensitively; altitude bounds are inclusive; `seen_since` filters `last_seen_at`. Observation `from/to` filters `event_time` (records with null event time are excluded from that bounded query); session `from/to` filters `started_at`; all intervals are half-open. Reject `from >= to`, negative bucket sizes, unknown filter names, nonfinite altitude, and `limit` outside 1–200 with `Problem` code `invalid_query`.

`Problem` schema is `{code:string,message:string,details:object|null,request_id:string}`. Use 400 invalid filters or over-limit query window/page size, 404 unknown resource, 422 malformed path/body, 503 database/schema not ready, 500 unexpected fault. Never expose SQL, stack traces, secret values, or raw provider responses. Zero counts and `data_available:false` are distinct.

`AircraftSummary`: `icao24,first_seen_at,last_seen_at,last_observation,current_session_id,image,flight_info`. `FlightSession`: `session_id,icao24,receiver_id,started_at,last_observed_at,ended_at|null,first_observation_id,last_observation_id,callsign|null,minimum_distance_m|null,minimum_distance_observation_id|null`. `EnrichmentResult`: `state,provider_id|null,fetched_at|null,expires_at|null,match_confidence|null,data|null,attribution|null,safe_error_code|null`. `AnalyticsSummary`: `window:{from,to},receiver_id|null,data_available,aircraft_count,message_count|null,message_rate_per_second|null,message_metrics_available,aircraft_update_count,position_update_count,distance:{minimum_observed_m|null,valid_position_count},signal_metrics:[{kind,unit,calibration_status|null,aggregation,value|null}],receiver_state:{state,uptime_seconds|null,definition}`. Message metrics count only `record_kind=decoded_frame`; if decoder supplies only `aircraft_update`, message count/rate are null and `message_metrics_available=false`. Observed tracks are local observations; origin/destination in `flight_info` is external and provenance-tagged. Missing metrics remain null/empty and are never encoded as zero.

## WebSocket contract v1

`/api/v1/stream` sends `{schema_version:1,event_id:string,event_type:string,event_time:RFC3339 UTC,data:object}`. Types: `aircraft.updated` (`data.aircraft:AircraftSummary`), `aircraft.removed` (`data:{icao24,reason:"stale"}`), `status.updated` (`data` is status schema). `event_time` is server emission time and distinct from aircraft event/ingestion times. No replay guarantee in v1. On reconnect client exponential backoff capped at 30 sec plus jitter, then refresh REST status and aircraft snapshots. Server closes overloaded/idle clients; close codes and limits are documented in OpenAPI/deployment before implementation. Multi-worker operation requires shared event fanout or a documented single-worker restriction; in-process events alone do not promise cross-worker delivery.

## Provider adapter interfaces

`AircraftImageProvider.lookup(icao24, registration?, observed_at?)` returns `EnrichmentResult` with `data:{image_url,attribution,source_page,license}` where known. `FlightInfoProvider.lookup(callsign, observed_at, receiver_context?)` returns `data:{flight_id,origin,destination,provider_time,valid_from,valid_to}` plus match confidence. Provider names, credentials, terms, quota, coverage, permitted cache lifetime, and image rights are unresolved until selected/verified. Absence is `unconfigured`; missing/ambiguous/stale/unavailable are normal states. Core ingestion remains functional.

## Canonical environment variables

This is the sole canonical configuration table. `deployment-required` means no default is invented; secrets are injected by operator secret management. Exact hostnames/ports/providers are never inferred.

| Name | Required and purpose | Default / valid values | Secret | Missing/invalid behavior |
|---|---|---|---|---|
| `APP_ENV` | Required runtime environment | `development`, `test`, `production`; none | No | Fail startup. |
| `LOG_LEVEL` | Optional log threshold | `INFO`; `DEBUG/INFO/WARNING/ERROR/CRITICAL` | No | Invalid fails. |
| `API_BIND_HOST` | Deployment-required bind address | Explicit operator choice; none | No | Fail startup. |
| `API_PORT` | Deployment-required listen port | Explicit operator choice; none | No | Fail startup if absent/out of TCP range. |
| `CORS_ORIGINS` | Production required browser origins | Explicit origins, no wildcard default | No | Production fails absent/invalid. |
| `DB_HOST` | Required verified MySQL DNS/IP | No default | No | Fail startup. |
| `DB_PORT` | Required port from actual MySQL config | No default assumed | No | Fail startup. |
| `DB_NAME` | Required provisioned dedicated schema | No default | No | Fail startup. |
| `DB_USER` | Required least-privilege runtime account | No default | No | Fail startup. |
| `DB_PASSWORD` | Required runtime credential | Operator secret | Yes | Fail startup; redact. |
| `DB_CONNECT_TIMEOUT_SECONDS` | Optional bounded connection timeout | Positive implementation-selected value | No | Invalid fails. |
| `OPERATING_MODE` | Required hardware mode | `adsb` or `sdrpp_scanner`; no default | No | Fail; never auto-switch. |
| `RECEIVER_ID` | Required stable receiver identifier in ADS-B mode | Operator-selected ID, at most 96 characters; no default | No | Fail ADS-B startup if missing/invalid. |
| `RECEIVER_MODE` | Required only in ADS-B mode | `rtlsdr_usb`; `airspy_server` only after exact protocol verified | No | ADS-B mode fails if absent/unsupported. |
| `RECEIVER_HOST` | Required only for network receiver | Verified address; none for direct USB | No | Selected adapter fails if needed and absent. |
| `RECEIVER_PORT` | Required only for network receiver | Current rtl_tcp port 1234 is known; no other default | No | Selected adapter fails if needed and absent. |
| `RECEIVER_LATITUDE` | Required for distance analytics | Decimal [-90,90], no default | No | Fail unless paired and valid. |
| `RECEIVER_LONGITUDE` | Required for distance analytics | Decimal [-180,180], no default | No | Fail unless paired and valid. |
| `DECODER_NAME` | Required in ADS-B mode | Approved pinned decoder; `readsb` candidate | No | ADS-B startup fails until selected. |
| `DECODER_INPUT_MODE` | Required in ADS-B mode | `direct_usb` candidate; bridge only after verified | No | Fail if unsupported/unverified. |
| `DECODER_OUTPUT_MODE` | Required in ADS-B mode | `readsb_json` candidate; exact listener/build configuration to verify | No | Fail unless compatible parser chosen/tested. |
| `DECODER_ENDPOINT` | Required for network output only | Verified endpoint; none otherwise | No | Fail when selected output requires it. |
| `FLIGHT_SESSION_SILENCE_SECONDS` | Required session closure policy | Positive configured value; none chosen | No | Production readiness blocked if absent/invalid. |
| `AIRCRAFT_STALE_AFTER_SECONDS` | Required stale-aircraft removal threshold for WebSocket | Positive configured value; none chosen | No | Production readiness blocked if absent/invalid. |
| `OBSERVATION_RETENTION_DAYS` | Required retention policy | Positive integer; `unlimited` only with explicit approval | No | Production readiness blocked if unset. |
| `IMAGE_PROVIDER` | Optional adapter selection | `disabled` or approved identifier | No | Absent => unconfigured. Unknown ID fails config validation. |
| `IMAGE_PROVIDER_CREDENTIAL` | Conditional provider secret | Provider-defined secret | Yes | Adapter unconfigured if required and absent. |
| `FLIGHT_PROVIDER` | Optional adapter selection | `disabled` or approved identifier | No | Absent => unconfigured. Unknown ID fails config validation. |
| `FLIGHT_PROVIDER_CREDENTIAL` | Conditional provider secret | Provider-defined secret | Yes | Adapter unconfigured if required and absent. |
| `AUDIO_SOURCE_MODE` | Optional audio adapter | `unconfigured` or approved identifier | No | Absent => unavailable; no readiness impact. |
| `AUDIO_SOURCE_CREDENTIAL` | Conditional audio secret | Provider-defined secret | Yes | Adapter unconfigured if required and absent. |
| `AUDIO_STATIONS_CONFIG` | Optional non-secret station list | Operator config reference; format TBD | No | Absent => empty list/unconfigured. |

Provider-specific endpoint names, ports, quotas and credentials are intentionally omitted until provider selection. No arbitrary API/audio URLs are accepted from browser input.

Container health probes call the liveness/readiness endpoints above. Probe interval, timeout and retry count are deployment-level settings to be selected for the target environment; this spec invents no probe timings or ports.

## Data health, retention and acceptance distinctions

Readiness: API + DB + schema only. Receiver/decoder offline or scanner mode changes component state but not API readiness. Provider/audio errors do not affect readiness. Retention and session silence interval are required policy inputs, but their durations remain unresolved. Tests must assert exact states, timestamps, schema fields, session boundaries, dedupe behavior, WebSocket envelopes, and ownership-release evidence. Simulated tests cannot prove USB/RF/bridge/provider/audio compatibility.
