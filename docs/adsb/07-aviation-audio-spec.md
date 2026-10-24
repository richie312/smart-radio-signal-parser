# ADS-B Application: Aviation Audio

> **Finalized contract note:** Station configuration and frontend controls remain in scope, but live playback is unavailable until source/protocol/codec/delivery are verified. Raw IQ/`rtl_tcp` is not browser audio. Exclusive receiver modes in [00](00-project-overview.md) prohibit simultaneous ADS-B/scanner use of the dongle.

## Batch 1 capability

Provide a configurable aviation frequency/station list and browser controls only after identifying a legitimate audio source. The UI may list station name, frequency, band/modulation if known, source status, and an explicit play/stop action. Configuration is local and editable through deployment configuration or a later approved settings interface.

## Source and delivery boundary

The existing `rtl_tcp` endpoint supplies RTL-SDR sample/control traffic; it does not itself provide decoded voice audio or a browser-ready audio stream. ADS-B decoding at 1090 MHz is separate from aviation voice reception. The current SDR scripts expect SDR++ Rigctl on port 4532, but the current Compose file does not declare SDR++ Rigctl. Do not claim those scripts or rtl_tcp provide a working audio source.

Before implementing playback, choose and verify one source:

- an independent network audio feed with permission and documented endpoint/codec; or
- a dedicated/independent receiver and audio streaming service; or
- another explicitly approved source with an established browser-compatible delivery path.

The adapter should expose station metadata and a playback URL/session through a safe backend contract. Do not proxy arbitrary user-supplied URLs (SSRF risk). If auth tokens are needed, issue short-lived URLs or proxy audio through a controlled service without leaking credentials to logs.

## Receiver limitations and arbitration

The approved operating model is exclusive: this application will not run ADS-B reception and scanner/audio reception simultaneously on the same RTL-SDR, regardless of theoretical tuner bandwidth. Current `rtl_tcp` command sets an initial frequency and sample rate; it does not establish a simultaneous voice channel. Do not retune the ADS-B receiver for audio while claiming continuous ADS-B reception. Use a separately verified audio source or report playback unconfigured. A future multi-receiver design requires separate approval.

## Deferred

Asynchronous frequency scanning, speech/squelch detection, and recording are deferred. No WAV binary is stored in MySQL. No audio path may alter existing Python scripts as part of this specification.

## Browser behavior

Show unavailable/configuration-required when there is no verified source. Provide accessible play/stop, volume and mute controls if supported, visible connection/error status, and browser autoplay-safe user initiation. Handle unsupported codec and network loss with actionable state. See [frontend](08-react-frontend-spec.md) and [security](09-docker-config-and-security.md).
