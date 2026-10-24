# ADS-B backend (software-only initial implementation)

FastAPI contract implementation for shared API v1. Decoder/receiver, enrichment providers, and audio are intentionally unconfigured. No aircraft fixtures are bundled and an empty repository is reported as unavailable data, never as live reception.

## Configuration

Runtime configuration follows `docs/adsb/12-shared-contracts-and-configuration.md`. The API fails closed when required application/database settings are missing. ADS-B receiver mode remains gated on verified decoder, input, and output selection; no adapter is started by this software-only slice. Scanner mode marks ADS-B reception inactive by mode.

Install `requirements.txt` in a project-specific environment, then run `uvicorn app.main:app` from this directory. Apply `migrations/001_initial.sql` separately with an operator-managed migration account after schema/network approval. Startup only checks the schema version and never performs DDL. This implementation does not connect to any currently running database during development.

The WebSocket implementation is single-process, sends an initial `status.updated` contract envelope and provides no replay or aircraft event fanout until ingestion/event integration exists. Deploy one worker until shared fanout is implemented.

## Tests

Run `python -m unittest discover -s tests` after installing declared dependencies. The unit tests use test-only values and do not simulate a live receiver.
