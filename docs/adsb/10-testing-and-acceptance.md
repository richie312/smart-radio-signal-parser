# ADS-B Application: Testing and Acceptance

> **Finalized contract note:** Use exact field/state/API assertions from [12](12-shared-contracts-and-configuration.md). Simulated tests do not prove USB acquisition, decoder compatibility, network bridge behavior, live provider terms, or browser audio delivery.

## Test layers

### Unit tests

- Configuration parsing, coordinate validation, API schema validation, callsign normalization, observation normalization, distance calculation, analytics bucket boundaries, cache behavior, and error mapping.
- Adapter state transitions and reconnect/backoff using fake streams.
- Repository transaction behavior and migration model validation against a disposable test database.
- React components for loading/empty/error/stale states, units, provenance, keyboard controls, and accessible audio controls.

### Integration tests

- FastAPI + disposable MySQL instance/schema with migrations and CRUD/history/analytics queries.
- Fake decoder/receiver emitting synthetic or captured decoded ADS-B fixtures; assert normalized observations persist and status updates.
- Mock enrichment providers for success, missing, ambiguous, rate-limit, timeout, stale cache, and provider failure.
- API/WebSocket or chosen live-update transport reconnect and snapshot consistency.
- Frontend against mocked API and a local integration backend.

### Simulated versus real-world validation

**Mock/simulated tests can prove:** API contracts, parsing, persistence, retry logic, frontend behavior, calculations, and provider failure handling.

**Only real receiver/hardware tests can prove:** USB access, RF tuning/sensitivity, selected direct-USB decoder path or any proposed `rtl_tcp` bridge, actual 1090 MHz reception, clean USB release and sequential mode switching, Airspy Server compatibility if selected, and real reception coverage. Simultaneous ADS-B/scanner operation is prohibited and is not an acceptance target.

**Only provider-account tests can prove:** live API credentials, quotas, rights, actual matching quality, and image availability. These must use test credentials or approved accounts and must not put secrets into fixtures/logs.

## Acceptance by component

- **Receiver/decoder**: configured adapter reports truthful state; raw sample input is not mistaken for decoded output; simulated decoded message reaches normalized contract; real hardware gate records selected decoder compatibility and tuner ownership.
- **Backend**: typed REST endpoints validate and bound inputs; liveness/readiness distinguish failure; DB outage is visible; enrichment outage does not break core endpoints; logs are structured and redacted.
- **Database**: migrations work from empty schema; indexes support history/time queries; account is least privilege; no audio binary data exists.
- **Enrichment/location**: each external value carries provider/time/status; missing data is normal; distance units and null behavior are correct; observed track remains distinct from route estimate.
- **Analytics**: counts use defined windows; rates identify time basis; unavailable signal metrics are omitted; coverage is described as observed positions, not RF contour.
- **Audio**: verify the VOHS station IDs against the current AAI eAIP, confirm the RTL-SDR switches exclusively from readsb to AM and back, and verify private browser MP3 playback. ADS-B status must show paused during audio and resume only after readsb reconnects.
- **Frontend**: displays receiver and ingestion state, aircraft list/detail, enrichment provenance, analytics, and audio status; handles empty/offline/stale/error states accessibly; no map or mobile UI required.
- **Deployment/security**: existing MySQL reused; no duplicate DB service; no real secrets in repository; existing runtime services/config are preserved unless separately approved.

## Release gate

Before implementation, review and approve all specifications and close blocking decisions on decoder input, SDR ownership, MySQL network identity, and API/audio provider scope. Before hardware-dependent release, record a separate real-SDR validation result. See [execution plan](11-agent-execution-plan.md).
