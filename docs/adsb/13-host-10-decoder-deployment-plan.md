# ADS-B decoder deployment plan for host .10

This is the approved deployment direction for the existing receiver topology. It is a plan, not evidence that the decoder is installed or running.

## Verified facts

- `192.168.1.10:1234` returned the `RTL0` greeting, identifying an `rtl_tcp` endpoint.
- From a container attached to `my_rasp_network`, TCP access succeeded to `.10:1234` and `.50:3306`. That Docker bridge currently contains only `redis-server`.
- `.10` did not accept connections on the probed decoded-feed ports `30002`, `30003`, `30005`, or `30152`.
- `.50:3306` returned a MySQL 8.0.45 greeting. Authentication and application-schema compatibility have not been tested.
- SSH to `richie@192.168.1.10` was denied (`publickey,password`). The host OS, active USB owner, service definitions, and device identity have not been inspected. No remote changes were made.

## Selected topology

Run the ADS-B decoder on `.10`, where the RTL-SDR is physically attached. The decoder owns the device directly in ADS-B mode and publishes structured aircraft updates to the application over the LAN. Do not make the application container claim USB ownership and do not point `readsb` at the current `rtl_tcp` IQ endpoint: upstream `readsb` documents direct RTL-SDR operation, while its [rtl_tcp input issue](https://github.com/wiedehopf/readsb/issues/133) documents that network IQ input is not currently supported by that path.

The selected output candidate is `readsb --net-json-port`, which upstream documents as one JSON line for each aircraft position update. Normalize these records as `record_kind=aircraft_update`; frame counts and frame rates remain unavailable. See the [readsb build and device documentation](https://github.com/wiedehopf/readsb) and [JSON position output option](https://github.com/wiedehopf/readsb/blob/dev/README.md).

Exact release/commit, Linux distribution, USB serial/device index, bind address, listener port, firewall rule, and service manager are deployment values to inspect and record on `.10` before installation. Do not assume a default port or silently replace its existing service.

## Execution sequence

1. Obtain authorized SSH access for `richie@192.168.1.10`. Access is currently blocked by public-key/password authentication, so execution cannot proceed remotely yet.
2. Read-only preflight on `.10`: record OS and architecture; list the RTL-SDR USB identity; inspect processes and service units using the device; inspect listeners and existing scanner configuration; verify storage and build dependencies. Do not print environment secrets.
3. Select and pin a readsb release/commit compatible with the host OS. Build or install it side-by-side with RTL-SDR support. Confirm `--device-type rtlsdr` and `--net-json-port` in that exact binary's help output. Do not enable a service at boot yet.
4. Save the current receiver/scanner service settings for rollback. Stop the active process or processes that may own the dongle. Confirm the kernel device is released using the host's available USB/process tools. Do not start readsb while ownership is uncertain.
5. Start readsb manually in ADS-B mode with explicit 1090 MHz tuning, direct RTL-SDR input, quiet logging, and JSON output bound only to the LAN address `.10`. Select the port after checking it is unused and allow it through the host firewall only from the application host/network. Record the exact command and version.
6. Verify that readsb acquires the expected physical device, remains stable, and emits lines matching captured fixtures and the adapter parser. Verify actual ADS-B reception when traffic is available; never substitute fixtures for the live status. Confirm the service stops cleanly and releases USB.
7. Only after manual acceptance, create a dedicated service definition with explicit stop/restart behavior and no automatic takeover. Keep the scanner mode separately controlled; it must stop readsb, confirm USB release, start the existing scanner owner, and report `sdrpp_scanner` status. Reverse the sequence to return to ADS-B mode.
8. From the application container on `my_rasp_network`, connect to `.10:<selected-json-port>` and verify JSON ingestion, timestamps, nullable fields, and truthful update metrics. Use `.50` as the existing database host after credentials and schema compatibility are verified; do not create another MySQL server.
9. Record acceptance evidence, then enable automatic service startup only if the user approves the validated switch and rollback behavior.

## Rollback

Stop the ADS-B decoder, confirm it released the RTL-SDR, then restore the saved scanner/`rtl_tcp` service state and verify that owner. Never restart the prior service while readsb may still hold the device. Report which owner is active after rollback.

## Current gate

The user has authorized planning and execution, but the only tested SSH attempt was denied. No service was stopped, no package was installed on `.10`, and no USB ownership or live RF test has been performed. Remote execution resumes once authorized SSH access is available.
