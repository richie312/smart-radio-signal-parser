# ADS-B Application: Backend Specification

> **Finalized contract note:** The authoritative REST/WebSocket schemas, status/readiness rules, and complete canonical environment table are in [12](12-shared-contracts-and-configuration.md). Where earlier illustrative API or configuration prose differs, document 12 takes precedence.

## Recommended stack and structure

Use Python with FastAPI and an ASGI server. This is a proposed Batch 1 service; no backend currently exists. Keep boundaries explicit:

```text
backend/app/
  api/              route handlers and request/response schemas
  core/             settings, logging, lifespan, error mapping
  receivers/        receiver/decoder adapters and ingestion lifecycle
  services/         aircraft, analytics, enrichment, audio status
  repositories/     database access and transaction boundaries
  models/           persistence models and migrations
```

No implementation or dependency version is prescribed here. Pin and review versions during implementation.

## Configuration

Load typed settings at startup using the sole canonical table in [12](12-shared-contracts-and-configuration.md). Settings are mode-aware: receiver/decoder settings are required only in ADS-B mode; provider/audio configuration is optional; DB, coordinates, session interval and retention follow the required conditions defined there.

Fail startup on malformed required settings, invalid coordinate pairs, unsupported receiver modes, or incomplete database configuration. Do not include secret values in logs or error responses. See [09](09-docker-config-and-security.md).

## REST API contract (versioned `/api/v1`)

Use JSON, UTC RFC 3339 timestamps, stable field names, pagination limits, and documented error bodies.

| Method/path | Purpose |
|---|---|
| `GET /health/live` | Process liveness; no downstream dependency checks. |
| `GET /health/ready` | API/database/schema readiness; receiver and decoder state remain separate in `/api/v1/status`. |
| `GET /api/v1/status` | Current receiver, decoder, database-ingestion, and configured site status. |
| `GET /api/v1/aircraft` | Current aircraft snapshot; filters for callsign, hex address, altitude bounds, and freshness; bounded pagination. |
| `GET /api/v1/aircraft/{icao24}` | Aircraft identity, latest observation, and available enrichment with provenance. |
| `GET /api/v1/aircraft/{icao24}/observations` | Time-bounded, paginated observation history. |
| `GET /api/v1/aircraft/{icao24}/sessions` | Time-bounded, paginated observed reception sessions. |
| `GET /api/v1/analytics/summary` | Counts/rates and coverage for a validated time window. |
| `GET /api/v1/analytics/timeseries` | Bucketed counts/rates with maximum window and bucket count. |
| `GET /api/v1/enrichment/{icao24}` | Cached enrichment/status; provider calls should not block general aircraft queries. |
| `GET /api/v1/audio/config` | Available configured stations and playback capability/status, excluding secrets. |

Audio control endpoints, if needed, are read-only selection preferences and must not retune the ADS-B receiver unless a separately approved resource-arbitration design exists. Exact route schemas are implementation contract work to finalize before coding.

## Live updates

WebSocket `/api/v1/stream` is required for live aircraft data. Use only event types and envelope in [12](12-shared-contracts-and-configuration.md): `aircraft.updated`, `aircraft.removed`, `status.updated`. The initial REST snapshot is authoritative. Client reconnect and snapshot refresh follow that contract; multi-worker fanout needs a shared mechanism or documented single-worker deployment.

## Validation and errors

- Validate ICAO 24-bit hexadecimal address, coordinate ranges, timestamp range, pagination, filter combinations, and time-window bounds.
- Normalize callsigns by trimming padding while preserving a raw decoder value where useful.
- Treat absent or invalid decoded fields as unknown; do not synthesize measurements.
- Return `400` for invalid/over-limit queries, `404` for unknown aircraft, `503` for database/schema not ready, and `500` only for unexpected faults. Use the exact `Problem` object in [12](12-shared-contracts-and-configuration.md).
- Avoid returning SQL, stack traces, secret values, internal paths, or raw provider errors.
- Bound expensive history/analytics endpoints; enforce maximum page size and date span from the shared contract. Do not add independent undocumented limits.

## Logging and observability

Structured logs include timestamp, level, component, request/correlation ID, and safe error code. Track last successful decoder message, decoder connection state, messages accepted/rejected, persistence failures, reconnect count, DB latency, enrichment cache hit/miss/failure, and event client count. Do not log every aircraft message at info level. Redact credentials and provider tokens.

## Lifecycle and health

Startup validates settings, opens DB pool, checks migration compatibility, and starts only workers for the selected mode. Shutdown stops accepting new work, cancels workers gracefully, closes sockets and DB pool. Liveness is process-only. Readiness requires API + DB + compatible schema; receiver/decoder faults degrade reception without making an otherwise healthy API unready. See [12](12-shared-contracts-and-configuration.md).

## Cross-spec references

Use normalized fields from [03](03-receiver-and-decoder-spec.md), table definitions from [04](04-mysql-data-model.md), and metric definitions from [06](06-reception-analytics-spec.md). Frontend route use is in [08](08-react-frontend-spec.md).
