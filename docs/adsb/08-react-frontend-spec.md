# ADS-B Application: React Frontend

> **Finalized contract note:** Use the exact REST schemas, query names, cursor pagination, status states and WebSocket v1 envelope in [12](12-shared-contracts-and-configuration.md). Mobile and Leaflet remain deferred.

## Scope and structure

Build a desktop-first React + TypeScript single-page dashboard. Mobile application and Leaflet/map rendering are deferred. Suggested areas: `app` routing/layout, `api` typed client, `features/receiver`, `features/aircraft`, `features/analytics`, `features/audio`, and shared accessible components. Exact bundler/state library are implementation decisions; avoid adding state-management complexity before needed.

## Pages and components

- **Dashboard**: receiver/decoder/DB ingestion status, last message age, current aircraft count, message rate, time-window analytics, recent aircraft.
- **Aircraft table**: ICAO24, callsign, last seen, altitude, speed, track, distance, stale/position state. Sorting/filtering and bounded pagination.
- **Aircraft detail panel/page**: latest observation, available history list/summary, image with attribution, external flight info with provenance/confidence, and observed-vs-external distinctions. No map in this batch.
- **Analytics section**: aircraft/message counts and rates, time series, range/coverage summaries, signal metric only when available.
- **Aviation audio controls**: configured stations and source status; play initiated by user, never imply availability without a configured source.
- **Global status**: connected/degraded/offline states with last-updated time.

## API client and state

Use a centralized typed API client for `/api/v1`; handle request IDs and stable error codes. REST snapshot is authoritative. If WebSocket is implemented, consume versioned event envelopes and refresh REST snapshot after reconnect. Deduplicate events by entity/time or event ID if supplied. Keep transient loading/error state separate from valid empty data. Do not store API secrets in browser code.

## Loading, empty, stale, and error states

- Initial loading has a clear skeleton/status.
- No aircraft is a valid empty state with receiver health context.
- Stale/offline reception shows last successful message time and does not present old positions as live.
- Enrichment missing/ambiguous/unavailable is non-blocking and labeled.
- Audio unavailable, unsupported, or disconnected is explicit.
- Network errors allow retry; filter validation errors are shown near controls.

## Accessibility and usability

Semantic headings, table headers, keyboard-operable filters and controls, visible focus, sufficient contrast, textual status in addition to color, descriptive image alt text, and labels for units (ft, kt, degrees, km/NM). Respect reduced motion. Audio requires explicit user gesture and accessible mute/volume controls.

## Security

No credentials in client bundle. Configure exact allowed origin and use secure transport in exposed deployments. Render external strings as text, sanitize/validate URL schemes for images/media, and follow image attribution requirements. See [02](02-backend-spec.md), [05](05-flight-enrichment-and-location.md), and [07](07-aviation-audio-spec.md).
