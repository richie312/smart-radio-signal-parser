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

- `docker-compose.yaml` defines only `rtl_tcp`, using host networking, USB mapping, and TCP 1234. `Dockerfile` installs rtl-sdr and runs rtl_tcp.
- `rtl_tcp` is a receiver protocol carrying control/IQ samples, not decoded ADS-B output; see the [upstream rtl_tcp implementation](https://github.com/osmocom/rtl-sdr/blob/master/src/rtl_tcp.c).
- `src/controller.py` and `src/recorder.py` default to TCP 4532 and send SDR++ Rigctl commands. `src/scanner.py` uses `RadioController`. Compose does not define an SDR++ Rigctl server.
- No ADS-B decoder, backend, frontend, MySQL schema/configuration, or audio server exists in the repository.
- User-provided constraint: a container named `mysql` exists on a Docker network. Actual network membership/aliases, port, MySQL version/config, database and user must be inspected.

## Operating modes and safe switching

Exactly one process may own the physical RTL-SDR. No automatic takeover.

1. Stop the active receiver/scanner process or container.
2. Confirm process exit and USB release.
3. Start only the selected mode.
4. Verify device ownership and expected output/status; report mode, owner and resulting state. If release/acquisition cannot be verified, report `error` and do not start another owner.

Preserve `src/controller.py`, `src/recorder.py`, and `src/scanner.py` behavior. This procedure does not imply a mode supervisor exists or Rigctl is currently running.

## Confirmed, candidate, and unverified

**Confirmed:** repository facts above and user-supplied deployment constraints. **Documented candidate:** `readsb` upstream documents direct RTL-SDR device operation and output interfaces ([upstream](https://github.com/wiedehopf/readsb)); this does not prove our image/build/hardware path. **Unverified:** readsb input from this exact rtl_tcp feed, any bridge, Airspy Server decoder interoperability, external providers, audio source and deployment topology.

## Blocking decisions and acceptance

ADS-B mode prefers direct USB ownership. Pin and test an actual decoder build, device permissions, 1090 MHz operation, output parsing and clean release before declaring the adapter implementable. A network bridge needs protocol/build documentation and a separate executable integration test. Also verify Docker/MySQL topology and provisioning owner; approve session-silence and retention values; select providers/audio source and terms. No arbitrary retention/session/provider values are assumed.

The specs must provide stable contracts, truthful states, separate simulated and hardware/provider acceptance, and keep core reception independent of optional integrations. Implementation starts only after user approval.

See [architecture](01-system-architecture.md), [backend](02-backend-spec.md), [receiver/decoder](03-receiver-and-decoder-spec.md), [deployment](09-docker-config-and-security.md), and [testing](10-testing-and-acceptance.md).
