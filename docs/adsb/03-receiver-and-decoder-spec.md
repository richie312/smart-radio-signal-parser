# ADS-B Application: Receiver and Decoder Specification

> **Implementation update (October 2026):** The readsb TCP JSON adapter has been implemented and the user confirmed live data persisted on `.10`. Compose now has a single-owner radio controller that switches between readsb and receive-only AM audio; see the [Docker runbook](../docker-runbook.md). The design notes below describe the original planning state and should not override the current Compose configuration.

## Current behavior and limits

The current Compose service runs `rtl_tcp` with USB device access and listens on TCP 1234. Its command sets initial center frequency to 819000 Hz (819 kHz), not the 1090 MHz ADS-B band; ADS-B mode needs explicit verified tuner configuration. This is an RTL-SDR network-control/sample interface. It is not itself decoded ADS-B message output. Existing Python scripts speak SDR++ Rigctl on TCP 4532; Compose does not currently declare that server. Preserve `src/controller.py`, `src/recorder.py`, and `src/scanner.py` and their current protocol assumptions.

The signal path contains distinct representations:

1. RF received at the antenna.
2. Sampled raw IQ data (or a receiver-specific sample stream) provided by RTL-SDR/Airspy.
3. Mode S/ADS-B frames produced by a decoder.
4. Parsed aircraft fields/JSON or another structured decoder output.

Never connect an ADS-B message parser directly to port 1234 while labeling the bytes decoded aircraft data.

## Decoder candidate and selection gate

**Documented implementation path:** run a pinned `readsb` build with RTL-SDR support compiled in, configured for `--device-type rtlsdr`, and give that process direct exclusive USB ownership in ADS-B mode. Its upstream build instructions document RTLSDR support and the receiver mode. For backend ingestion, use the upstream JSON position output (`--net-json-port`) as `record_kind=aircraft_update`; this output is an aircraft position/state feed, not a count of every RF frame, so frame message metrics remain unavailable. Select and pin the maintained distribution/version and exact JSON listener configuration during implementation. These docs establish feature support, not this repository's end-to-end hardware operation.

Do not use `readsb` as if it directly consumes this repo's `rtl_tcp` stream; that network path is not selected. Direct USB is the chosen documented path, pending the hardware gate below. No bridge is needed for the selected path. Airspy Server remains a separate adapter decision. `readsb_json` is the chosen output candidate; confirm the pinned build exposes it and validate its exact line schema against fixtures before implementation. Its aggregated updates do not prove per-frame message counts.

## Adapter contract

Define an abstract adapter with:

- `validate_config(config)`: reject unsupported/incomplete mode before connection.
- `connect()`, `disconnect()`, and `health()`: return state, last transition, last data time, endpoint mode, and sanitized error code.
- `start_stream()` or equivalent decoder handoff; ADS-B mode explicitly owns the device; scanner mode must not start this adapter.
- `reconnect()` with backoff and cancellation.
- Capability metadata: receiver type, supported band/mode, stream format, optional signal metrics, and whether remote control/audio is actually available.

Adapters must not promise identical RF tuning controls if protocols differ. A common configuration selects receiver mode but preserves adapter-specific validated options.

### Existing rtl_tcp service

Current service is a raw-IQ receiver protocol endpoint at port 1234, not the selected decoded input path. Direct USB ownership is preferred for ADS-B mode and requires stopping rtl_tcp so it releases USB. No decoder-to-rtl_tcp network path is selected. A bridge requires protocol/build documentation and an executable integration test proving the complete path. Do not silently alter Compose or scripts.

### Airspy Server adapter

Provide a configurable endpoint adapter only after confirming exact Airspy Server product/protocol and decoder/client compatibility. Host, port, protocol version, TLS/auth needs, and sample format are unresolved. Report unsupported capabilities rather than emulating them.

## Normalized message contract

Use only `DecodedMessageEnvelope` v1 from [12](12-shared-contracts-and-configuration.md). Decoder/source `event_time` is distinct from backend-assigned `ingested_at`. Null means unknown/not reported; zero is not a missing-value sentinel. Signal metrics are reported measurements with kind/unit, not derived analytics. Metadata is bounded and sanitized.

## Internal status transitions and reconnect behavior

The public status contract is only `online`, `degraded`, `offline`, `unconfigured`, or `error` as defined in [12](12-shared-contracts-and-configuration.md); older/internal transitional labels below are not API states. Receiver/decoder loss degrades reception but does not make a DB-ready API unready. In scanner mode, ADS-B status is `unconfigured` with reason `inactive_by_mode`.

States: `stopped`, `connecting`, `streaming`, `degraded`, `backoff`, `failed`. Include `last_connected_at`, `last_message_at`, reconnect attempts, and safe error code. On disconnect, close stale sockets, retry with exponential backoff (e.g. 1–30 seconds plus jitter; tune as configuration), reset on stable connection, and expose stale/offline data age. Do not drop into an infinite tight retry loop. If the receiver is available but no messages arrive, report connected/no-data separately from disconnected.

## Signal metrics

Only persist metrics actually provided by the selected decoder/receiver, with field provenance and units. Signal strength from decoder-specific values may not be calibrated RSSI. Never fabricate SNR/noise floor from raw presence or browser data.

## Test strategy

- Unit tests for adapter configuration, state transitions, malformed frames, normalization and reconnect timing using fake sockets.
- Integration tests with captured/synthetic sample or decoded-message fixtures and a local mock decoder endpoint.
- Network contract test against selected decoder output in a container without real SDR.
- Separate real-hardware test for RF reception, USB ownership/release and mode switching. Airspy compatibility requires its own integration test if selected; no simultaneous mode test is in scope.
- Confirm existing scripts remain unmodified and their expected Rigctl interface is documented.

Decoder evidence: [readsb upstream repository](https://github.com/wiedehopf/readsb) documents direct RTL-SDR builds, receiver selection, and JSON position output. Hardware/device permissions, selected build, JSON schema, clean USB release, and actual RF reception remain to be tested before the adapter is production-ready.
