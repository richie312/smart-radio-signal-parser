# ADS-B Batch 1 Specifications

These documents define the documentation baseline for the ADS-B web application. They do not authorize implementation; review and approval are a gate before coding begins.

## Documents

1. [Project overview](./docs/adsb/00-project-overview.md)
2. [System architecture](./docs/adsb/01-system-architecture.md)
3. [Backend specification](./docs/adsb/02-backend-spec.md)
4. [Receiver and decoder specification](./docs/adsb/03-receiver-and-decoder-spec.md)
5. [MySQL data model](./docs/adsb/04-mysql-data-model.md)
6. [Flight enrichment and location](./docs/adsb/05-flight-enrichment-and-location.md)
7. [Reception analytics](./docs/adsb/06-reception-analytics-spec.md)
8. [Aviation audio](./docs/adsb/07-aviation-audio-spec.md)
9. [React frontend](./docs/adsb/08-react-frontend-spec.md)
10. [Docker configuration and security](./docs/adsb/09-docker-config-and-security.md)
11. [Testing and acceptance](./docs/adsb/10-testing-and-acceptance.md)
12. [Agent execution plan](./docs/adsb/11-agent-execution-plan.md)

## Reading order

Start with the overview and architecture. The receiver/decoder, backend, data model, and enrichment documents establish the core contracts. Analytics, audio, frontend, deployment, and testing build on those contracts. The execution plan is last because it governs implementation after the specification set is reviewed and approved.

## Status and evidence labels

Each specification distinguishes repository observations and user-supplied constraints from proposed designs and decisions still requiring verification. External decoder references are candidates, not declarations that the software is installed or operational.
