# ADS-B Batch 1: Agent Execution Plan

> **Finalized contract note:** This plan is future workflow only. No implementation starts until user approval. Coordinator must read the approved specs and shared contracts in [12](12-shared-contracts-and-configuration.md) before assigning work.

## Gate before any implementation

Implementation must not begin until the full specification set in this directory is reviewed and approved. The coordinator records the approved revision and decisions. If review changes contracts, update the specs first and circulate the new baseline.

## Coordinator responsibilities

1. Inspect current source, Compose, Dockerfile, and repository status before assigning work; specifically verify the live MySQL network/name and receiver/decoder compatibility available in the target environment.
2. Resolve or explicitly track blocking choices: decoder input path and build, USB-release verification during exclusive mode switching, MySQL network/database provisioning, session/retention values, provider selection, and audio source.
3. Create a shared contract baseline for normalized observations, API schemas, database migrations, configuration names, and status/events. Only coordinator (or an explicitly assigned contract owner) edits these shared contracts.
4. Assign isolated files/directories and clear dependencies. Agents must not independently rewrite shared contracts or overwrite another workstream's files.
5. Review diffs, run the specified tests, resolve integration failures, inspect security and migration behavior, and verify existing radio scripts/config are preserved.
6. Merge only after component acceptance gates and document any deviation from approved specs.

## Workstreams and ownership

| Workstream | Responsibility | Depends on |
|---|---|---|
| Architecture/contracts | Shared event/observation/API/config schemas and integration decisions | Approved specs; owns contract files |
| Receiver/decoder | Adapter lifecycle, decoder process/client integration, simulated fixtures | Receiver compatibility decision; shared observation contract |
| Backend/database | FastAPI routes, ingestion orchestration, migrations/repositories, health | Shared API/data contracts; verified MySQL target |
| Enrichment/analytics | Provider adapters/cache, distance and summary/time-series services | Data contract; provider approvals/credentials handled securely |
| Audio | Audio source adapter/status and browser delivery contract | Verified independent source and receiver arbitration decision |
| Frontend | React dashboard, typed client, states/accessibility | Approved API schemas and event contract |
| Integration/testing | Compose/network integration, end-to-end simulation, acceptance evidence | Component interfaces and deployment facts |

## Suggested implementation order

1. Coordinator verifies environment facts and locks contract baseline.
2. Backend/database and receiver/decoder develop against mocks in parallel, owning separate directories.
3. Integrate ingestion into persistence and verify simulated decoded fixtures.
4. Add analytics and enrichment against stable tables/services; external APIs remain mocked until credentials/terms approved.
5. Frontend implements against typed mock fixtures, then integrates with backend.
6. Audio work starts only after source and receiver arbitration are confirmed; otherwise show configuration-required status only.
7. Integration/testing validates deployment network, component health, recovery, security, and hardware/provider gates separately.

## Shared contract controls

- Contracts have a named owner and version; changes require a short impact note and coordinator approval before dependent work proceeds.
- Each workstream edits only assigned paths. Cross-cutting edits are proposed as patches to coordinator, not applied independently.
- No two agents edit a migration, OpenAPI schema, Compose file, or shared type file concurrently.
- Keep fixtures versioned with schema version and avoid real credentials or personal data.
- The coordinator inspects the full diff and checks preserved files before integrating any contribution.

## Integration gates

1. **Contract gate**: decoder envelope, API schemas, DB entities, config names, and status lifecycle agree.
2. **Data gate**: simulated messages persist once according to policy and produce expected API response/analytics.
3. **Resilience gate**: DB/decoder/provider loss yields the documented status and recovery behavior.
4. **UI gate**: dashboard matches API and handles stale/empty/error cases accessibly.
5. **Deployment gate**: new services join actual network, reuse existing MySQL, expose only approved ports, and do not take over SDR unexpectedly.
6. **Hardware/provider gate**: real SDR, Airspy, RF coverage, and live API tests are explicitly recorded apart from simulation.

No deployment or implementation begins solely because an agent completed its isolated task; coordinator verifies all gates and approved scope.

## Required finalized controls

- Before assignment, read every user-approved document, inspect repository status and existing files, and verify Docker/MySQL deployment facts. Resolve blocking decoder, hardware-ownership, database-provisioning, session/retention and provider/audio decisions first.
- Freeze the contracts in [12](12-shared-contracts-and-configuration.md) before parallel implementation. One contract owner approves all interface changes; no two agents edit shared schemas, migrations, event types, config, or Compose concurrently.
- Enforce `adsb` versus `sdrpp_scanner` as mutually exclusive owners. Switching requires stopping the process, confirming USB release, starting the target, and verifying ownership/status. No automatic takeover.
- Integrate by dependency: contracts -> receiver/backend and DB against mocks -> ingestion/persistence -> analytics/enrichment -> frontend/WebSocket -> deployment -> real hardware/provider gates. Audio playback waits for its source gate; configuration/status UI may report unconfigured.
- Coordinator inspects every diff and test/evidence report before merging and verifies existing scripts/config are preserved. No implementation starts until user approval; this plan does not authorize agents now.
