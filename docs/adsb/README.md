# ADS-B Batch 1 Specifications

These specifications are approved for Batch 1 implementation, subject to the architecture, hardware, database, provider, and deployment gates documented here. The shared contracts in document 12 are authoritative.

## Documents

1. [Project overview](00-project-overview.md)
2. [System architecture](01-system-architecture.md)
3. [Backend specification](02-backend-spec.md)
4. [Receiver and decoder specification](03-receiver-and-decoder-spec.md)
5. [MySQL data model](04-mysql-data-model.md)
6. [Flight enrichment and location](05-flight-enrichment-and-location.md)
7. [Reception analytics](06-reception-analytics-spec.md)
8. [Aviation audio](07-aviation-audio-spec.md)
9. [React frontend](08-react-frontend-spec.md)
10. [Docker configuration and security](09-docker-config-and-security.md)
11. [Testing and acceptance](10-testing-and-acceptance.md)
12. [Coordinator execution plan](11-agent-execution-plan.md)
13. [Shared contracts and canonical configuration](12-shared-contracts-and-configuration.md)
14. [Implementation checklist](implementation-checklist.md)
15. [Host .10 decoder deployment plan](13-host-10-decoder-deployment-plan.md)

## Reading order

Read overview and architecture first, then shared contracts before component specifications. The coordinator plan applies only after the user approves the specification set.
