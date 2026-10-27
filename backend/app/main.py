"""FastAPI application implementing ADS-B shared REST and WebSocket contract v1."""
from __future__ import annotations

import base64
import asyncio
from datetime import datetime, timedelta, timezone
import json
import math
import uuid
from typing import Any

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .contracts import ComponentStatus, Problem, normalize_icao, parse_time, utc_now
from .repositories import EmptyRepository, MySQLRepository, Repository
from .readsb import ReadsbIngestor
from .settings import Settings


def _status(state: str, *, error: str | None = None, details: dict | None = None,
            last: datetime | None = None, message: datetime | None = None):
    return ComponentStatus(state=state, updated_at=utc_now(), last_success_at=last,
                           last_message_at=message, error_code=error, details=details or {})


def _cursor_decode(cursor: str | None) -> int:
    if not cursor: return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
        if value < 0: raise ValueError
        return value
    except Exception: raise ValueError("cursor is invalid") from None


def _page(items: list[dict], limit: int, offset: int):
    page = items[offset:offset + limit]
    next_cursor = base64.urlsafe_b64encode(str(offset + limit).encode()).decode().rstrip("=") if len(items) > offset + limit else None
    return {"items": page, "next_cursor": next_cursor}


def create_app(repository: Repository | None = None, settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="ADS-B API", version="1.0.0")
    app.state.repository = repository
    app.state.settings = settings or Settings.from_env()
    app.state.started = False
    app.state.ingestor = None
    app.state.ingestor_task = None

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        allowed_by_path = {
            "/api/v1/aircraft": {"callsign", "icao24", "altitude_min_ft", "altitude_max_ft", "seen_since", "limit", "cursor"},
            "/api/v1/analytics/summary": {"from", "to", "receiver_id"},
            "/api/v1/analytics/timeseries": {"from", "to", "bucket_seconds", "receiver_id"},
        }
        for suffix in ("/observations", "/sessions"):
            if request.url.path.startswith("/api/v1/aircraft/") and request.url.path.endswith(suffix):
                allowed_by_path[request.url.path] = {"from", "to", "limit", "cursor"}
        if request.url.path in allowed_by_path:
            unknown = sorted(set(request.query_params.keys()) - allowed_by_path[request.url.path])
            if unknown:
                response = JSONResponse(status_code=400, content=Problem(code="invalid_query", message="Unknown query parameter", details={"fields": unknown}, request_id=rid).model_dump(mode="json"))
                response.headers["X-Request-ID"] = rid
                return response
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    def problem(request: Request, status: int, code: str, message: str, details: dict | None = None):
        return JSONResponse(status_code=status, content=Problem(code=code, message=message, details=details, request_id=getattr(request.state, "request_id", str(uuid.uuid4()))).model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return problem(request, 422, "invalid_request", "Request validation failed", {"fields": [str(e.get("loc", [])) for e in exc.errors()]})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        # Do not expose exception text, SQL, paths, or credentials.
        return problem(request, 500, "internal_error", "An unexpected server error occurred")

    def repo() -> Repository:
        if app.state.repository is not None: return app.state.repository
        cfg = app.state.settings
        if cfg.config_errors: raise RuntimeError("configuration_invalid")
        return MySQLRepository(cfg.mysql)

    def db_health():
        try: ready, error = repo().check_ready()
        except Exception: ready, error = False, "database_unavailable"
        return ready, error

    @app.on_event("startup")
    async def startup():
        cfg = app.state.settings
        # Test factories inject repository/settings. Production config errors fail closed.
        if cfg.config_errors and cfg.app_env != "test":
            raise RuntimeError("required configuration is missing or invalid")
        if cfg.operating_mode == "adsb":
            repository_for_ingestion = repo()
            app.state.repository = repository_for_ingestion
            try:
                await asyncio.to_thread(repository_for_ingestion.ensure_receiver, cfg.receiver_id, {
                    "receiver_mode": "rtlsdr_usb", "decoder": "readsb",
                    "input_mode": "direct_usb", "output_mode": "readsb_json",
                    "endpoint": cfg.decoder_endpoint,
                })
            except Exception:
                # Receiver configuration is DML only. Keep API startup/readiness independent
                # from the receiver, while ingestion reports a safe database error.
                app.state.receiver_registration_error = "database_unavailable"
            ingestor = ReadsbIngestor(cfg.decoder_endpoint, cfg.receiver_id, cfg.decoder_version, repository_for_ingestion)
            app.state.ingestor = ingestor
            app.state.ingestor_task = asyncio.create_task(ingestor.run())
        app.state.started = True

    @app.on_event("shutdown")
    async def shutdown():
        ingestor = app.state.ingestor
        task = app.state.ingestor_task
        if ingestor is not None:
            ingestor.stop()
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @app.get("/health/live")
    def live(): return {"state": "online"}

    @app.get("/health/ready")
    def ready(request: Request):
        ok, error = db_health()
        if ok: return {"state": "online"}
        return problem(request, 503, error or "database_unavailable", "Database or schema is not ready", {"database": {"state": "offline", "error_code": error}})

    @app.get("/api/v1/status")
    def status():
        cfg = app.state.settings
        db_ok, db_error = db_health()
        scanner = cfg.operating_mode == "sdrpp_scanner"
        mode_unknown = cfg.operating_mode not in {"adsb", "sdrpp_scanner"}
        base_unconfigured = _status("unconfigured", details={"reason": "not_configured"}).model_dump(mode="json")
        if scanner or mode_unknown:
            reason = "inactive_by_mode" if scanner else "configuration_required"
            rec = _status("unconfigured", error="invalid_configuration" if mode_unknown else None,
                          details={"mode": cfg.operating_mode or "unknown", "owner": "sdrpp_scanner" if scanner else "none", "last_message_at": None, "reconnect_attempts": 0, "reason": reason}).model_dump(mode="json")
            dec = _status("unconfigured", details={"name": None, "version": None, "last_message_at": None, "reason": reason}).model_dump(mode="json")
            ing = _status("unconfigured", details={"accepted_count": 0, "rejected_count": 0, "last_persisted_at": None, "reason": reason}).model_dump(mode="json")
        else:
            ingestor = app.state.ingestor
            if ingestor is None:
                rec_state, rec_error = "error", "invalid_configuration"
                decoder_state, decoder_error = "unconfigured", "decoder_unconfigured"
                ingestion_state, ingestion_error = "degraded", "decoder_unconfigured"
                last_message = last_persisted = None
                accepted = rejected = reconnects = 0
            else:
                rec_state, rec_error = ingestor.status()
                decoder_state, decoder_error = rec_state, rec_error
                accepted, rejected, reconnects = ingestor.accepted_count, ingestor.rejected_count, ingestor.reconnect_attempts
                last_message, last_persisted = ingestor.last_message_at, ingestor.last_persisted_at
                if ingestor.last_error_code == "database_unavailable" or getattr(app.state, "receiver_registration_error", None):
                    ingestion_state, ingestion_error = "degraded", "database_unavailable"
                elif accepted and rec_state == "online":
                    ingestion_state, ingestion_error = "online", None
                else:
                    ingestion_state, ingestion_error = "degraded", rec_error or "no_updates_received"
            rec = _status(rec_state, error=rec_error, last=last_message, message=last_message,
                          details={"mode": "rtlsdr_usb", "owner": "adsb_decoder", "last_message_at": last_message, "reconnect_attempts": reconnects}).model_dump(mode="json")
            dec = _status(decoder_state, error=decoder_error, last=last_message, message=last_message,
                          details={"name": "readsb", "version": cfg.decoder_version, "last_message_at": last_message}).model_dump(mode="json")
            ing = _status(ingestion_state, error=ingestion_error, last=last_persisted,
                          details={"accepted_count": accepted, "rejected_count": rejected, "last_persisted_at": last_persisted}).model_dump(mode="json")
        site = {"latitude": None, "longitude": None, "configured": False}
        return {"operating_mode": cfg.operating_mode or "unknown", "api": _status("online").model_dump(mode="json"),
                "database": _status("online" if db_ok else "offline", error=db_error).model_dump(mode="json"),
                "receiver": rec, "decoder": dec, "ingestion": ing, "audio": base_unconfigured, "site": site}

    def check_query_window(request: Request, from_: str | None, to: str | None):
        try:
            start = parse_time(from_, "from") if from_ else None
            end = parse_time(to, "to") if to else None
            if start and end and start >= end: raise ValueError("from must be earlier than to")
            if start and end and end - start > timedelta(days=366): raise ValueError("query window exceeds 366 days")
            return start, end, None
        except ValueError as e: return None, None, problem(request, 400, "invalid_query", str(e))

    @app.get("/api/v1/aircraft")
    def aircraft(request: Request, callsign: str | None = None, icao24: str | None = None, altitude_min_ft: float | None = None, altitude_max_ft: float | None = None, seen_since: str | None = None, limit: int = Query(50, ge=1, le=200), cursor: str | None = None):
        try:
            normalized = normalize_icao(icao24) if icao24 else None
            if altitude_min_ft is not None and not math.isfinite(altitude_min_ft) or altitude_max_ft is not None and not math.isfinite(altitude_max_ft): raise ValueError("altitude bounds must be finite")
            if altitude_min_ft is not None and altitude_max_ft is not None and altitude_min_ft > altitude_max_ft: raise ValueError("altitude_min_ft must not exceed altitude_max_ft")
            since = parse_time(seen_since, "seen_since") if seen_since else None
            offset = _cursor_decode(cursor)
        except ValueError as e: return problem(request, 400, "invalid_query", str(e))
        ok, error = db_health()
        if not ok: return problem(request, 503, error or "database_unavailable", "Database or schema is not ready")
        try: items = repo().list_aircraft(callsign=callsign.strip() if callsign else None, icao24=normalized, altitude_min_ft=altitude_min_ft, altitude_max_ft=altitude_max_ft, seen_since=since, limit=limit + offset + 1)
        except Exception: return problem(request, 503, "database_unavailable", "Database query failed")
        return _page([_aircraft_summary(row) for row in items], limit, offset)

    @app.get("/api/v1/aircraft/{icao24}")
    def aircraft_detail(request: Request, icao24: str):
        try: key = normalize_icao(icao24)
        except ValueError as e: return problem(request, 422, "invalid_icao24", str(e))
        ok, error = db_health()
        if not ok: return problem(request, 503, error or "database_unavailable", "Database or schema is not ready")
        row = repo().get_aircraft(key)
        if row is None: return problem(request, 404, "not_found", "Aircraft not found")
        return _aircraft_summary(row)

    def history(request: Request, icao24: str, from_: str | None, to: str | None, limit: int, cursor: str | None, session: bool):
        try:
            key = normalize_icao(icao24); start, end, err = check_query_window(request, from_, to)
            if err: return err
            offset = _cursor_decode(cursor)
        except ValueError as e: return problem(request, 422, "invalid_icao24", str(e))
        ok, error = db_health()
        if not ok: return problem(request, 503, error or "database_unavailable", "Database or schema is not ready")
        fn = repo().sessions if session else repo().observations
        values = fn(key, **{"from": start, "to": end, "limit": limit + offset + 1})
        return _page(values, limit, offset)

    @app.get("/api/v1/aircraft/{icao24}/observations")
    def aircraft_observations(request: Request, icao24: str, from_: str | None = Query(None, alias="from"), to: str | None = None, limit: int = Query(50, ge=1, le=200), cursor: str | None = None):
        return history(request, icao24, from_, to, limit, cursor, False)

    @app.get("/api/v1/aircraft/{icao24}/sessions")
    def aircraft_sessions(request: Request, icao24: str, from_: str | None = Query(None, alias="from"), to: str | None = None, limit: int = Query(50, ge=1, le=200), cursor: str | None = None):
        return history(request, icao24, from_, to, limit, cursor, True)

    @app.get("/api/v1/analytics/summary")
    def analytics_summary(request: Request, from_: str = Query(..., alias="from"), to: str = Query(...), receiver_id: str | None = None):
        start, end, err = check_query_window(request, from_, to)
        if err: return err
        ok, error = db_health()
        if not ok: return problem(request, 503, error or "database_unavailable", "Database or schema is not ready")
        raw = repo().analytics(**{"from": start, "to": end, "receiver_id": receiver_id})
        count = int(raw.get("aircraft_count") or 0)
        frames = raw.get("frame_count")
        seconds = (end - start).total_seconds()
        return {"window": {"from": start, "to": end}, "receiver_id": receiver_id, "data_available": bool(raw.get("observation_count")), "aircraft_count": count,
                "message_count": frames, "message_rate_per_second": frames / seconds if frames is not None else None,
                "message_metrics_available": frames is not None, "aircraft_update_count": int(raw.get("update_count") or 0), "position_update_count": int(raw.get("position_count") or 0),
                "distance": {"minimum_observed_m": None, "valid_position_count": int(raw.get("position_count") or 0)}, "signal_metrics": [],
                "receiver_state": {"state": "unconfigured", "uptime_seconds": None, "definition": "No verified receiver adapter is configured"}}

    @app.get("/api/v1/analytics/timeseries")
    def analytics_timeseries(request: Request, from_: str = Query(..., alias="from"), to: str = Query(...), bucket_seconds: int = Query(..., gt=0), receiver_id: str | None = None):
        start, end, err = check_query_window(request, from_, to)
        if err: return err
        if (end - start).total_seconds() / bucket_seconds > 1000: return problem(request, 400, "invalid_query", "query exceeds 1000 buckets")
        # No fabricated bucket metrics when no frame-level source is configured.
        ok, error = db_health()
        if not ok: return problem(request, 503, error or "database_unavailable", "Database or schema is not ready")
        return {"window": {"from": start, "to": end}, "bucket_seconds": bucket_seconds, "receiver_id": receiver_id, "data_available": False, "buckets": []}

    @app.get("/api/v1/enrichment/{icao24}")
    def enrichment(request: Request, icao24: str):
        try: normalize_icao(icao24)
        except ValueError as e: return problem(request, 422, "invalid_icao24", str(e))
        return {"image": {"state": "unconfigured", "provider_id": None, "fetched_at": None, "expires_at": None, "match_confidence": None, "data": None, "attribution": None, "safe_error_code": None},
                "flight_info": {"state": "unconfigured", "provider_id": None, "fetched_at": None, "expires_at": None, "match_confidence": None, "data": None, "attribution": None, "safe_error_code": None}}

    @app.get("/api/v1/audio/config")
    def audio_config(): return {"state": "unconfigured", "stations": []}

    @app.websocket("/api/v1/stream")
    async def stream(websocket: WebSocket):
        await websocket.accept()
        now = utc_now()
        event = {"schema_version": 1, "event_id": str(uuid.uuid4()), "event_type": "status.updated", "event_time": now.isoformat().replace("+00:00", "Z"), "data": status()}
        try:
            await websocket.send_json(event)
            # Explicit single-worker, no-replay contract. No fake aircraft updates are emitted.
            while True: await websocket.receive_text()
        except WebSocketDisconnect: return

    return app


def _aircraft_summary(row: dict[str, Any]) -> dict[str, Any]:
    """Project DB rows into the exact shared AircraftSummary field set."""
    observation_fields = ("observation_id", "record_kind", "icao24", "receiver_id", "event_time", "ingested_at", "source_event_id", "callsign", "latitude_deg", "longitude_deg", "altitude_ft", "ground_speed_kt", "track_deg", "vertical_rate_fpm", "squawk", "on_ground", "signal_metric", "signal_metric_kind", "signal_metric_unit", "decoder_name", "decoder_version")
    observation = {key: _utc_value(row.get(key)) for key in observation_fields}
    return {"icao24": row["icao24"], "first_seen_at": _utc_value(row["first_seen_at"]), "last_seen_at": _utc_value(row["last_seen_at"]),
            "last_observation": observation, "current_session_id": None,
            "image": {"state": "unconfigured", "provider_id": None, "fetched_at": None, "expires_at": None, "match_confidence": None, "data": None, "attribution": None, "safe_error_code": None},
            "flight_info": {"state": "unconfigured", "provider_id": None, "fetched_at": None, "expires_at": None, "match_confidence": None, "data": None, "attribution": None, "safe_error_code": None}}


def _utc_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return value


app = create_app()
