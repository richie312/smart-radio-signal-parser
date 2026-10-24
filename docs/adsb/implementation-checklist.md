# ADS-B Batch 1 Implementation Checklist

Track against the approved specifications. The shared contracts in [12](12-shared-contracts-and-configuration.md) are authoritative. Do not mark hardware, database, provider, or playback gates complete based on mocks.

## Preflight

- [x] Read all ADS-B specifications and record dependency order.
- [x] Inspect repository files, scripts, Compose, working tree, and test setup.
- [x] Preserve the existing root `README.md` modification and radio scripts.
- [x] Inspect Docker containers and networks read-only.
- [x] Verify the Docker route from `my_rasp_network` to the supplied LAN hosts: the network is `172.19.0.0/16`, currently contains only `redis-server`, and that container can reach `192.168.1.10:1234` and `192.168.1.50:3306`.
- [x] Identify receiver and database protocol greetings: `.10:1234` returns `RTL0` (rtl_tcp); `.50:3306` returns a MySQL 8.0.45 handshake. Common decoded feed ports 30002, 30003, 30005, and 30152 on `.10` did not accept connections.
- [ ] **Blocked:** verify MySQL authentication, schema version, and operator provisioning. No credentials were supplied to the test process, and no schema query or write was attempted. No local `mysql` container exists; use the existing host at `.50`.
- [ ] **Blocked:** verify decoder acquisition/output and physical USB release. The dongle is reachable through rtl_tcp on `.10`, but the selected `readsb` candidate is documented for direct USB and no decoded feed was found on the probed ports. The active USB owner and safe mode-switch behavior on `.10` remain unverified.
- [x] Prepare the host-specific direct-USB decoder deployment and rollback plan in [13](13-host-10-decoder-deployment-plan.md). Remote execution remains blocked until SSH access to `.10` is authorized.
- [ ] Confirm exact session silence and observation retention values with the owner before deployment.
- [ ] Confirm API bind host/port and production CORS origins before deployment.

## Shared contracts

- [x] Canonical operating modes, normalized envelope, REST/WebSocket types, data model, health states and configuration are in [12](12-shared-contracts-and-configuration.md).
- [ ] Freeze/generated OpenAPI and frontend types from the canonical schemas before integration.
- [ ] Record any accepted contract changes centrally before component work proceeds.

## Receiver and decoder

- [ ] Select and pin a decoder build. `readsb` direct RTL-SDR USB is a documented candidate, not validated here.
- [ ] Verify decoder output mode and whether records are decoded frames or aggregated aircraft updates.
- [ ] Implement adapter lifecycle and truthful public status; scanner mode must leave ADS-B inactive.
- [ ] Test sequential stop/release/start/verify mode switching; never permit simultaneous USB ownership.
- [ ] If a network bridge is proposed, require protocol/build evidence and a real end-to-end integration test.
- [ ] Verify Airspy Server only if selected.

## Backend and MySQL

- [x] Implement the initial FastAPI routes, validation/errors, liveness/readiness, status, and required WebSocket envelope. Software-only slice; test execution is blocked because FastAPI/Pydantic are not installed.
- [x] Add an operator-applied MySQL migration and repository boundary for receivers, aircraft, observations, flight sessions, enrichment cache and ingestion health. Migration has not been applied; database connection/schema compatibility remains blocked pending verified MySQL access and operator provisioning.
- [ ] Implement event-time/ingestion-time handling, source-event deduplication, session closure and bounded retention.
- [x] Run backend unit/API tests against the explicit empty test repository using `C:\Users\Richie\envs\radio`; 8 tests passed. MySQL integration remains blocked pending credentials and schema verification.
- [ ] Integrate only after existing MySQL network/schema/user is verified and provisioned by the database operator.

## Analytics and enrichment

- [ ] Implement observed counts, frame/update rates, distance/coverage and measured signal metrics with availability/provenance.
- [ ] Keep image/flight adapters disabled until providers, credentials, terms, quotas, coverage and cache rules are approved.
- [ ] Mock provider outcomes; verify enrichment failure never blocks core ingestion.

## Aviation audio

- [ ] Implement station metadata/configuration and explicit unconfigured controls.
- [ ] Enable playback only after source, rights, protocol, codec, delivery and browser support are verified.
- [ ] Confirm audio does not retune or share the ADS-B-owned dongle; no scanning or recording in Batch 1.

## Frontend

- [x] Implement the initial React + TypeScript dashboard, aircraft list/detail, analytics, enrichment provenance, mode/receiver health and disabled audio controls. Build is blocked because frontend dependencies are not installed.
- [ ] Use typed REST/WebSocket contracts and loading, empty, stale, offline, unconfigured and error states.
- [x] Clearly label every mock aircraft/data view as **TEST DATA — NOT LIVE RECEPTION**; never present fixtures as live.
- [ ] Verify accessibility, units, image attribution and reconnect snapshot refresh.

## Integration and release

- [ ] Test contract/API/DB/WebSocket integration using synthetic decoded fixtures.
- [ ] Test failure/recovery for DB, decoder, providers and WebSocket clients.
- [ ] Verify new containers use inspected Docker topology and existing MySQL only; do not create a second DB server.
- [ ] Preserve root README and existing radio scripts; inspect all diffs before integration.
- [ ] Record actual tests separately from hardware/provider acceptance evidence.
- [ ] Obtain user approval of implementation plan and remaining deployment choices before deployment.
