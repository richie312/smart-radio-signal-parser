# ADS-B Application: Docker Configuration and Security

> **Finalized contract note:** `rtl_tcp` uses host networking; do not assume reachability via the MySQL network. Inspect networks, aliases, port bindings, host platform and actual MySQL configuration first. The only canonical environment variable table is in [12](12-shared-contracts-and-configuration.md).

## Topology

The existing Compose file contains `rtl_tcp` only, uses `network_mode: host`, maps `/dev/bus/usb`, and exposes receiver TCP 1234 through its process arguments. Preserve existing services/configuration during the documentation task and preserve them during later implementation unless a separately reviewed change is approved.

The task context reports a pre-existing `mysql` container on a Docker network. Compose in this repository does not declare it. Before implementation, inspect actual network membership, aliases, port bindings, host platform, and MySQL configuration. New backend services may attach to the verified MySQL network, but that does not make host-network `rtl_tcp` reachable through MySQL DNS. Reuse the existing server; do not define another MySQL service. Publish only operator-approved browser-facing ports.

## Suggested services (proposed, not present)

- `backend`: FastAPI API and ingestion lifecycle.
- `decoder`: selected ADS-B decoder if it can be deployed separately and the chosen receiver path supports it.
- `frontend`: static React bundle or development server as appropriate.
- In `adsb` mode, stop the existing `rtl_tcp` service before the decoder acquires USB directly. In scanner mode, start only the configured SDR++ scanner receiver stack; identify which process actually holds USB during preflight.
- Existing external `mysql` remains externally managed.

Whether decoder belongs in Compose or on the host depends on USB ownership/protocol compatibility. Do not add it until the input path is verified. Use Compose external-network declaration only after the real network name is confirmed.

## Environment configuration

Use only the canonical names in [12](12-shared-contracts-and-configuration.md). Do not maintain an alternate list or add guessed ports/provider-specific variables. Do not commit real credentials or operational `.env` files. Example files, if approved later, contain placeholders only. Prefer Docker secrets or operator-managed secret mounts. Avoid logging complete connection strings.

## Health, startup, and recovery

Backend liveness and readiness are distinct. Liveness checks process only. Readiness requires API startup, database connectivity, and compatible schema; receiver/decoder loss degrades reception but does not make an otherwise healthy API unready. Provider/audio failures do not affect readiness. Compose dependency order is not proof of readiness; backend must report connection state. Graceful shutdown closes streams and DB connections.

## Network and least privilege

- Use a dedicated DB/schema and app account with minimum table privileges; keep migration credentials separate where possible.
- Restrict backend/API exposure to intended LAN/origin; do not bind publicly without authentication and transport-security review.
- Restrict CORS to configured frontend origins.
- Avoid privileged containers; map only required USB device access to the receiver/decoder owner.
- Do not expose decoder output ports to host unless needed; prefer internal network.
- Validate any configurable external URLs to prevent SSRF.
- Redact secrets and avoid credentials in health endpoint payloads.

See [architecture](01-system-architecture.md) and [backend](02-backend-spec.md).
