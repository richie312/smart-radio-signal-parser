# ADS-B Application: Docker Configuration and Security

## Topology

Compose defines a `radio_control` service built from the root `Dockerfile`, based on a pinned upstream RTL-SDR-enabled readsb image with rtl_fm and FFmpeg added. It maps `/dev/bus/usb` and owns the tuner. It runs readsb for ADS-B or an AM audio pipeline for one selected station, never both. The API reaches JSON output at `radio-control:30006` and authenticated control/audio endpoints at `radio-control:8090`.

`adsb_api` is built from `backend/Dockerfile`, joins the external `my_rasp_network`, and binds host port 8010 to loopback only. The API has no USB device mapping and no Docker socket. It proxies the private MP3 stream; neither decoder nor audio ports are published to the host. MySQL remains external at `.50`.

The services require a local, ignored `.env`. `RADIO_CONTROL_TOKEN` must be a locally generated secret shared by the API and radio controller. The API validates station IDs against the repository's Hyderabad VOHS station list; it does not accept arbitrary frequencies or remote media URLs.

## Receiver arbitration

On one tuner, ADS-B and airband are exclusive. Starting audio stops readsb and pauses aircraft observations; stopping audio restarts readsb. The existing host-installed readsb service must be stopped and disabled before Compose takes USB ownership. Stop Compose `radio_control` before restoring that host service or starting another SDR/scanner owner. The current design needs a second independent receiver or separate authorized audio source for simultaneous ADS-B and voice.

## Health and security

- Compose service ordering is not readiness; the API retries the decoder connection and reports receiver state separately from database readiness.
- Keep radio control endpoints on the internal Docker network; do not publish them to the LAN.
- Use the shared token for all mode-control and audio-stream requests. Do not log or expose it.
- Restrict API exposure to the intended local workstation/tunnel. Do not bind it publicly without authentication and transport-security review.
- Map only the RTL-SDR USB bus into the single device-owning radio controller. Keep MySQL migration credentials separate from the API runtime account.
- The audio pipeline is receive-only and limited to the station IDs in the local catalogue. Verify applicable local rules before sharing or rebroadcasting audio.

See the [Docker runbook](../docker-runbook.md) for setup, mode switching, and rollback.
