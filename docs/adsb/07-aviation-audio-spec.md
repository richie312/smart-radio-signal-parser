# ADS-B Application: Aviation Audio

> **Current implementation:** Station Monitor switches the Compose radio controller from readsb to a receive-only AM pipeline and proxies MP3 audio through the API. The user interface and service are implemented; the new hardware path still needs live acceptance on `.10`.

## Batch 1 capability

The initial station catalogue covers Rajiv Gandhi International Airport, Hyderabad (VOHS), from AAI's eAIP. The UI lists station, frequency, AM mode, and state with an explicit start/stop action.

## Source and delivery boundary

The radio controller owns the RTL-SDR. It runs readsb JSON at 1090 MHz in ADS-B mode, or rtl_fm AM tuned to the selected station and FFmpeg MP3 encoding in audio mode. The API proxies the stream; no decoder or audio port is published to the host. This does not integrate SDR++ Rigctl or change the existing scanner scripts.

Before implementing playback, choose and verify one source:

- an independent network audio feed with permission and documented endpoint/codec; or
- a dedicated/independent receiver and audio streaming service; or
- another explicitly approved source with an established browser-compatible delivery path.

The adapter should expose station metadata and a playback URL/session through a safe backend contract. Do not proxy arbitrary user-supplied URLs (SSRF risk). If auth tokens are needed, issue short-lived URLs or proxy audio through a controlled service without leaking credentials to logs.

## Receiver limitations and arbitration

The single-tuner operating model is exclusive. Starting audio stops readsb and pauses ADS-B ingestion; stopping audio restarts readsb. Simultaneous reception requires a second independent tuner or a separate authorized audio source.

## Deferred

Asynchronous frequency scanning, speech/squelch detection, and recording are deferred. No WAV binary is stored in MySQL. No audio path may alter existing Python scripts as part of this specification.

## Browser behavior

Show unavailable/configuration-required when there is no verified source. Provide accessible play/stop, volume and mute controls if supported, visible connection/error status, and browser autoplay-safe user initiation. Handle unsupported codec and network loss with actionable state. See [frontend](08-react-frontend-spec.md) and [security](09-docker-config-and-security.md).
