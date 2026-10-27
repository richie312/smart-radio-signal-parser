# ADS-B Application: Project Overview

## Purpose and goals

Batch 1 defines a desktop ADS-B reception and monitoring application. It receives from a selected receiver path, decodes Mode S/ADS-B data, stores aircraft observations in the existing MySQL service, exposes a versioned API, and presents reception status and aircraft data in a React + TypeScript frontend. It also supports a mutually exclusive SDR++ scanner mode.

## Batch 1 scope

- Two exclusive modes: **ADS-B** (decoder owns RTL-SDR) or **SDR++ scanner** (existing scanner workflow owns it).
- Receiver/decoder health, observations and flight sessions, REST queries, WebSocket live updates, reception analytics, fixed receiver coordinates, optional image/flight enrichment adapters.
- Aviation station configuration and frontend controls. Live audio remains unavailable until source, protocol, codec and delivery are verified.
- Dedicated application database/schema and least-privilege user on existing `mysql` container.

## Non-goals

- Simultaneous ADS-B and SDR++ scanner/audio operation on one dongle; automatic takeover.
- Mobile app, Leaflet/map, GPS, asynchronous frequency scanning, speech detection, audio recording.
- Satellite/weather, KiwiSDR, local SDR aggregation, experimental signal processing, or future tabs.
- WAV/audio binary storage in MySQL, replacing existing scripts, or treating `rtl_tcp` as decoded ADS-B/browser audio.

## Repository facts

- `docker-compose.yaml` defines a single-owner `radio_control` service with USB mapping and an `adsb_api` service on the external `my_rasp_network`. The root `Dockerfile` wraps a pinned upstream readsb image, adding rtl_fm and FFmpeg for receive-only airband audio.
- `rtl_tcp` is a receiver protocol carrying control/IQ samples, not decoded ADS-B output; see the [upstream rtl_tcp implementation](https://github.com/osmocom/rtl-sdr/blob/master/src/rtl_tcp.c).
- `src/controller.py` and `src/recorder.py` default to TCP 4532 and send SDR++ Rigctl commands. `src/scanner.py` uses `RadioController`. Compose does not define an SDR++ Rigctl server.
- The repository contains the ADS-B API, React frontend, MySQL migration, and Docker runbook. The Station Monitor switches the single tuner between ADS-B and Hyderabad airband audio.
- The user confirmed a live end-to-end run on `.10` using host-installed readsb: API/database/receiver/decoder/ingestion reported online and observations were persisted. The new Compose-managed mode switch still needs to be applied and verified on `.10`.
- MySQL remains external at `.50`; `my_rasp_network` is external and must exist on the Docker host.

## Operating modes and safe switching

Exactly one process may own the physical RTL-SDR. No automatic takeover.

1. Stop the active receiver/scanner process or container.
2. Confirm process exit and USB release.
3. Start only the selected mode.
4. Verify device ownership and expected output/status; report mode, owner and resulting state. If release/acquisition cannot be verified, report `error` and do not start another owner.

Preserve `src/controller.py`, `src/recorder.py`, and `src/scanner.py` behavior. This procedure does not imply a mode supervisor exists or Rigctl is currently running.

## Confirmed, candidate, and unverified

**Confirmed:** the current host-installed readsb path delivered live observations to the API and MySQL on `.10`, as reported by the user. The AAI eAIP supplies the VOHS frequency presets. The new receive-only AM pipeline and Compose ownership cutover need live verification on `.10`. **Unverified:** Airspy Server interoperability and external providers.

## Blocking decisions and acceptance

ADS-B and airband audio modes use exclusive USB ownership. See the [Docker runbook](../docker-runbook.md) for the Compose mode switch and host transition procedure. Also approve session-silence and retention values and select enrichment providers. No arbitrary retention/session/provider values are assumed.

The specs must provide stable contracts, truthful states, separate simulated and hardware/provider acceptance, and keep core reception independent of optional integrations. Implementation starts only after user approval.

See [architecture](01-system-architecture.md), [backend](02-backend-spec.md), [receiver/decoder](03-receiver-and-decoder-spec.md), [deployment](09-docker-config-and-security.md), and [testing](10-testing-and-acceptance.md).
