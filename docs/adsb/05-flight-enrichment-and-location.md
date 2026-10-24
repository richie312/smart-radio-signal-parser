# ADS-B Application: Flight Enrichment and Location

> **Finalized contract note:** Provider adapters follow the interfaces and `EnrichmentResult` shape in [12](12-shared-contracts-and-configuration.md). Provider selection, credentials, terms, quotas, coverage and cache policy remain unresolved; all such adapters may be disabled without affecting ingestion.

## Principles

Local decoder observations are primary evidence. External APIs enrich presentation; their failure must never block decoding, observation persistence, or core aircraft queries. Separate observed aircraft tracks from externally supplied schedule/route information in storage and UI.

## Provider adapters

Implement interfaces behind provider-specific adapters:

- **Aircraft image adapter**: lookup by ICAO24 and/or registration only when mapping is reliable; return image URL, attribution/photographer, source page, license/usage metadata, provider timestamp, and cache expiry where permitted.
- **Flight-information adapter**: lookup a flight by a normalized callsign/flight identifier and time context; return candidate flight identifier, origin, destination, scheduled/estimated data only if provided, match confidence, provider, fetch time, and validity window.

No provider is selected or credentialed by this specification. Verify APIs, authentication, commercial/personal terms, attribution, privacy, rate limits, and cache rules before implementation. External provider names and credentials are unresolved decisions, not available resources.

## Callsign matching

Treat the decoder callsign as a reported aircraft identifier, not guaranteed airline flight number. Trim trailing spaces, normalize case for lookup while retaining the received value. Reject placeholders/invalid patterns. Match only within a time window and use provider-supported context; never infer an origin/destination solely from ICAO24. Store match state (`matched`, `ambiguous`, `not_found`, `unavailable`, `stale`) and confidence/provenance. Ambiguous matches should be shown as such or omitted.

## Caching, limits, and failures

Cache by provider + lookup key, apply provider-specific TTL and limits. Coalesce simultaneous requests for the same key; use bounded concurrency and backoff on 429/5xx. Do not retry permanent authorization/validation failures aggressively. Stale cache may be displayed with a stale timestamp if provider terms permit. Missing data is a normal state. Provider failure should yield `unavailable` metadata and safe diagnostic code, not fail the aircraft endpoint.

## Provenance model

Every enriched field shown to a user must identify its source/provider and retrieval time. For routes, distinguish:

- **Observed track**: local ADS-B position/time samples from this receiver (may be partial and discontinuous).
- **External route information**: provider-supplied origin/destination or schedule inference, with match confidence and timestamp.

Do not connect an external origin/destination to the observed track as if the aircraft was locally seen there.

## Receiver location and distance

Store a fixed configured receiver latitude/longitude (WGS84 decimal degrees) per receiver. GPS integration is deferred. A valid aircraft position and receiver location allow great-circle distance calculation (Haversine or equivalent); return kilometers and nautical miles with documented rounding. Reject absent/invalid coordinates; distance is null when either location is missing.

Minimum observed distance is the minimum computed from valid received aircraft positions for the defined flight/session or retention window. Store the observation/time that produced the minimum or calculate from indexed observations. It is an observed minimum and may exceed true closest approach due to sparse reception. Do not describe it as exact closest approach.

## Privacy and display

Do not expose provider credentials or internal payloads. Follow image attribution/license requirements. Provide clear labels for external estimates and observed data. Do not promise route availability or identity resolution.

See [data model](04-mysql-data-model.md), [backend](02-backend-spec.md), and [frontend](08-react-frontend-spec.md).
