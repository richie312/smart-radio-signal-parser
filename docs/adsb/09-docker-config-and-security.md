# ADS-B Application: Docker Configuration and Security

> **Finalized contract note:** `rtl_tcp` uses host networking; do not assume reachability via the MySQL network. Inspect networks, aliases, port bindings, host platform and actual MySQL configuration first. The only canonical environment variable table is in [12](12-shared-contracts-and-configuration.md).

## Topology

Compose retains the existing `rtl_tcp` service unchanged: it uses `network_mode: host`, maps `/dev/bus/usb`, and exposes receiver TCP 1234 through its process arguments. It now also defines an `adsb_api` backend service built from `backend/Dockerfile`. The API joins the pre-existing external `my_rasp_network` and binds host port 8010 to loopback only. It has no USB device mapping and does not start a decoder.

The verified Docker network is `my_rasp_network` (`172.19.0.0/16`); it currently contains `redis-server`. The MySQL host is external at `.50`; no MySQL service is defined here. Reuse that server and do not define another one. The API is connected to this bridge for database access. The host-network `rtl_tcp` service is not attached to this bridge, and its port 1234 is IQ data rather than decoded ADS-B. The `.10` direct-USB decoder remains a separate, unverified deployment gate.

The service requires a local, ignored `.env` file. Start-up must fail closed when required database or mode configuration is absent. The committed `.env.example` contains no credentials and leaves database name/user and ADS-B decoder fields unset. The API image has been built successfully; container start remains blocked pending provisioned database settings. The container is not running.

## Remaining services and gates

- `decoder`: selected ADS-B decoder if it can be deployed separately and the chosen receiver path supports it; current plan is direct USB ownership on `.10`.
- `frontend`: static React bundle or development server as appropriate.
- In `adsb` mode, stop the existing `rtl_tcp` service before the decoder acquires USB directly. In scanner mode, start only the configured SDR++ scanner receiver stack; identify which process actually holds USB during preflight.
- Existing external `mysql` remains externally managed.

Do not add a decoder container until the direct-USB path and sequential stop/release/start/verify procedure have been tested on `.10`. The API service itself never claims the SDR.

## Environment configuration

Use only the canonical names in [12](12-shared-contracts-and-configuration.md). Do not maintain an alternate list or add guessed ports/provider-specific variables. Do not commit real credentials or operational `.env` files. Copy `.env.example` to `.env` locally and fill only the provisioned MySQL schema/account values; `.env` is ignored by Git. Prefer Docker secrets or operator-managed secret mounts for production. Avoid logging complete connection strings.

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
