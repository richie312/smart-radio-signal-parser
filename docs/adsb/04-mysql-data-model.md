# ADS-B Application: MySQL Data Model

> **Finalized contract note:** Shared observation/session fields, unique key/dedupe semantics, retention policy requirements and API-to-DB meanings are defined in [12](12-shared-contracts-and-configuration.md). This specification reuses the existing `mysql` container only; its network, version, port and provisioning owner must be inspected/confirmed first.

## Database and access

Use the existing `mysql` container on its inspected network. The deployment/database operator is responsible for provisioning a dedicated application database/schema and least-privilege runtime user; the application owner provides the required secret through approved secret management. The runtime account receives only necessary DML privileges on that schema; migration DDL privileges are separate where practical. Actual server version, network alias, port, schema name and credentials must be verified. Never put credentials in tracked files.

Use UTC `DATETIME(3)` or UTC-normalized timestamps consistently; document MySQL timezone behavior. Use migrations checked into the application repository. Migration runs must be explicit and repeatable; normal startup may validate schema version but should not silently perform destructive changes.

## Tables

### `receivers`

- `receiver_id` (PK, stable configured string)
- `name`, `receiver_type` (`rtlsdr_usb`, verified Airspy Server adapter identifier, or future string). `rtl_tcp` is a transport protocol, not the physical receiver type or a decoded data source.
- `enabled`, `configuration_json` (sanitized non-secret adapter options)
- `latitude_deg`, `longitude_deg`, `location_label` nullable until configured
- `created_at`, `updated_at`

Keep secrets outside this row or in a secret store. Enforce paired coordinates and range validation in application and, where supported, DB constraints.

### `aircraft`

- `icao24` (PK, normalized six-hex address)
- `first_seen_at`, `last_seen_at`
- `last_callsign`, `last_squawk` nullable convenience fields
- `created_at`, `updated_at`

This is a current identity/index record, not a claim of a real-world registration identity.

### `aircraft_observations`

- `observation_id` (monotonic PK)
- `record_kind` (`decoded_frame` or `aircraft_update`)
- `icao24` FK, `receiver_id` FK
- `event_time` (nullable decoder/source event time), `ingested_at` (backend acceptance time)
- `source_event_id` nullable, stable decoder identity when supplied
- nullable callsign, latitude/longitude, altitude ft, ground speed kt, track deg, vertical rate fpm, squawk, on-ground flag
- optional `signal_metric` + `signal_metric_kind` + `signal_metric_unit`; decoder/receiver-reported only
- `decoder_name` required, `decoder_version` nullable
- `metadata_json` for bounded future-compatible fields; avoid duplicating primary query fields

Indexes: `(icao24,event_time,observation_id)`, `(receiver_id,ingested_at)`, `(ingested_at)`, and unique `(receiver_id,decoder_name,source_event_id)` for non-null IDs (verify nullable unique semantics on target MySQL). Validate coordinates, finite numeric values, track range, and units before insert.

### `flight_sessions`

Observed reception grouping, not an authoritative airline itinerary. The contract and sessionization policy in [12](12-shared-contracts-and-configuration.md) is normative:

- `session_id` PK, `icao24` FK, `receiver_id` FK
- `started_at`, `last_observed_at`, `ended_at` nullable while active
- `first_observation_id`, `last_observation_id`
- `callsign` as observed during session
- `minimum_distance_m` and `minimum_distance_observation_id` nullable calculated values
- `created_at`, `updated_at`

Route data belongs in the separately provenance-tagged enrichment cache, not in observed session fields.

### `enrichment_cache`

- `cache_id` PK; `icao24`; `provider_id`, `data_kind` (`image`, `flight`), `lookup_key`
- normalized payload JSON or carefully selected columns; provider attribution/source URL where permitted
- `fetched_at`, `expires_at`, `status`, `last_error_code` (sanitized)
- unique `(provider_id, data_kind, lookup_key)` and indexes on expiry/address

Respect provider terms, cache rules, and image rights. Store no secrets in cached payload.

### `ingestion_health`

- `health_id` PK, `receiver_id` nullable FK, `component` (`api`, `database`, `receiver`, `decoder`, `ingestion`, `audio`)
- `state` (`online`, `degraded`, `offline`, `unconfigured`, `error`), `changed_at`, `last_success_at`, `last_message_at`, `reconnect_count`, `messages_seen`, `messages_rejected`
- sanitized `error_code`; optional bounded diagnostic JSON
- index `(receiver_id, changed_at)`

Keep current state in application memory/cache if appropriate, but persist transition history only at controlled rates.

## Relationships and write behavior

One receiver has many observations and health events. One aircraft has many observations and derived flight sessions. On each normalized observation, transactionally upsert aircraft first/last seen and insert observation/session update. Apply the stable `source_event_id` dedupe rule in [12](12-shared-contracts-and-configuration.md); never discard repeated position updates based only on matching values. Never store audio/WAV binaries in MySQL.

## Retention and scale

`OBSERVATION_RETENTION_DAYS` is required before production; no duration is chosen. Explicit unlimited retention requires owner approval and capacity planning. Estimate rows/day from measured rate and receiver count. Cleanup must be bounded/batched; define session and aggregate retention behavior before deleting observations. Backups and restore validation belong to deployment operations.

## Migrations and compatibility

Use forward migrations with tested upgrade path from empty schema. Destructive column/table changes require explicit reviewed migration and backup plan. Report schema version mismatch as not-ready. See [02](02-backend-spec.md) and [10](10-testing-and-acceptance.md).
