# ADS-B Application: System Architecture

> **Finalized contract note:** Operating modes are exclusive (`adsb` or `sdrpp_scanner`); use the safe switching procedure and contract definitions in [00](00-project-overview.md) and [12](12-shared-contracts-and-configuration.md). The existing `rtl_tcp` host-network service is not automatically reachable on the MySQL network.

## Component boundaries

1. **RF receiver**: exclusive operating mode selects either ADS-B decoder direct USB ownership or the SDR++ scanner workflow. A configured Airspy Server may be considered only after protocol/client verification. Supplies samples, not decoded aircraft records.
2. **Receiver adapter**: Configures/connects to a receiver and reports connection, ownership, and sample-source state. It does not decode aircraft messages unless explicitly implemented by the chosen decoder integration.
3. **ADS-B decoder**: Converts suitable 1090 MHz receiver samples into Mode S/ADS-B frames and derived aircraft fields. Decoder is a separate process/component selected after compatibility verification.
4. **Ingestion service**: Consumes decoder output, validates it, normalizes fields, associates receiver/site context, persists observations, and updates health metrics.
5. **FastAPI backend**: Serves REST resources, required live WebSocket events, health, analytics, and controlled audio configuration/status.
6. **MySQL**: Existing server, reached over its Docker network. A dedicated application schema/database and restricted application account are required.
7. **Enrichment adapters**: Optional outbound calls to image and flight-information providers, isolated from message ingestion.
8. **React + TypeScript frontend**: Calls backend APIs, presents receiver status, aircraft rows/details, analytics, enrichment, and aviation audio controls.
9. **Audio source**: Must be independently identified and tested. It is not implied by rtl_tcp or ADS-B decoding.

## Data flow

```text
antenna -> SDR receiver -> raw IQ/sample protocol -> decoder
                                           decoder frames/structured output
                                                     -> ingestion validation
                                                     -> MySQL observations/history
                                                     -> FastAPI REST / required WebSocket
                                                     -> React dashboard

MySQL aircraft identity/callsign -> optional enrichment adapters -> cached metadata
configured site coordinates + observed aircraft positions -> distance/coverage metrics
independent audio source -> backend-issued/configured playback URL -> browser audio control
```

The current `rtl_tcp` TCP stream is not a sequence of decoded aircraft records. ADS-B mode prefers direct USB ownership after stopping rtl_tcp. A network bridge must be selected and verified independently. The decoder adapter is not implementable before the selected build passes the hardware integration gate in [03](03-receiver-and-decoder-spec.md).

## Receiver and decoder boundary

The adapter contract in [03](03-receiver-and-decoder-spec.md) separates receiver configuration and health from decoder output. Normalize decoder-specific formats into an internal `AircraftObservation`/`DecodedMessage` contract. Avoid coupling API schemas directly to one decoder's JSON names.

The operating modes are mutually exclusive; do not assume simultaneous access. The existing scripts issue Rigctl commands to an SDR++ server, whereas Compose currently runs `rtl_tcp`; these are distinct services/protocols. Switching requires stop, confirmed USB release, start, and ownership/status verification.

## Configuration and secrets

Use only the canonical environment variables in [12](12-shared-contracts-and-configuration.md). No real credentials belong in tracked files. See [09](09-docker-config-and-security.md) for deployment handling.

Coordinates are fixed site configuration in Batch 1. Store both latitude and longitude as a paired validated value. Coordinate changes should be auditable/configured, not inferred from receiver GPS.

## Service interactions and resilience

- Core ingestion must continue when enrichment providers are unavailable.
- Database unavailability should stop durable ingestion, expose degraded health, and use bounded retry/backoff; do not claim durable buffering unless a queue is implemented.
- Decoder disconnection triggers reconnect with capped exponential backoff and jitter, with status timestamps and a visible degraded/offline state.
- Browser live updates are best-effort; REST remains authoritative for snapshots/history.
- Audio is an optional separate capability and must report unavailable when no verified source is configured.

## Deployment topology

New backend services may join the verified Docker network containing `mysql`; inspect actual topology first. This does not automatically connect them to host-network `rtl_tcp`. Reuse existing MySQL. Do not assume host networking for new services. See [09](09-docker-config-and-security.md).

## Cross-spec contracts

- Receiver/decoder lifecycle and normalized data: [03](03-receiver-and-decoder-spec.md)
- API and validation: [02](02-backend-spec.md)
- Persistence identities/observations: [04](04-mysql-data-model.md)
- External metadata and distance: [05](05-flight-enrichment-and-location.md)
- Metric definitions: [06](06-reception-analytics-spec.md)
- Audio boundaries: [07](07-aviation-audio-spec.md)
- Browser API behavior: [08](08-react-frontend-spec.md)
