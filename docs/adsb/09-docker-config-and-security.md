# ADS-B Application: Docker Configuration and Security

> **Current deployment:** Compose runs readsb with direct RTL-SDR USB ownership and the API on the external `my_rasp_network`. Follow the [Docker runbook](../docker-runbook.md) for configuration and host readsb cutover.

## Topology

Compose defines a `readsb` decoder service built from the root `Dockerfile`, which is based on a pinned upstream RTL-SDR-enabled image. The service maps `/dev/bus/usb` and joins `my_rasp_network`; the API reaches JSON position output at `readsb:30006`. The `adsb_api` service is built from `backend/Dockerfile`, joins the same external network, and binds host port 8010 to loopback only. The API has no USB device mapping.

The Docker network is external and must already exist. MySQL remains external at `.50`; no MySQL service is defined here. Reuse that server and do not define another one. The API is connected to the bridge for database and readsb access. Do not run host-installed readsb, `rtl_tcp`, or another SDR owner while the Compose readsb service owns the device.

The API requires a local, ignored `.env` file. Startup fails closed when required database or mode configuration is absent. `.env.example` contains no credentials and documents `tcp://readsb:30006` as the Compose endpoint. On an existing `.10` host installation, use the runbook's ownership transition before starting the containerized decoder.

## Remaining services and gates

- `frontend`: static React bundle or development server as appropriate.
- In `adsb` mode, readsb acquires USB directly. In scanner mode, stop readsb before starting the configured SDR++ scanner receiver stack.
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
