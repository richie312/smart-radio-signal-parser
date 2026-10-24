"""Canonical response models and validation helpers for contract v1."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

State = Literal["online", "degraded", "offline", "unconfigured", "error"]
RecordKind = Literal["decoded_frame", "aircraft_update"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Problem(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class ComponentStatus(BaseModel):
    state: State
    updated_at: datetime
    last_success_at: datetime | None = None
    last_message_at: datetime | None = None
    error_code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_id: int
    record_kind: RecordKind
    icao24: str
    receiver_id: str
    event_time: datetime | None
    ingested_at: datetime
    source_event_id: str | None
    callsign: str | None
    latitude_deg: float | None
    longitude_deg: float | None
    altitude_ft: float | None
    ground_speed_kt: float | None
    track_deg: float | None
    vertical_rate_fpm: float | None
    squawk: str | None
    on_ground: bool | None
    signal_metric: float | None
    signal_metric_kind: str | None
    signal_metric_unit: str | None
    decoder_name: str
    decoder_version: str | None


class FlightSession(BaseModel):
    session_id: str
    icao24: str
    receiver_id: str
    started_at: datetime
    last_observed_at: datetime
    ended_at: datetime | None
    first_observation_id: int
    last_observation_id: int
    callsign: str | None
    minimum_distance_m: float | None
    minimum_distance_observation_id: int | None


class EnrichmentResult(BaseModel):
    state: str
    provider_id: str | None = None
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    match_confidence: float | None = None
    data: dict[str, Any] | None = None
    attribution: dict[str, Any] | str | None = None
    safe_error_code: str | None = None


class AircraftSummary(BaseModel):
    icao24: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_observation: Observation
    current_session_id: str | None
    image: EnrichmentResult
    flight_info: EnrichmentResult


class Page(BaseModel):
    items: list[Any]
    next_cursor: str | None


class DecoderEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    record_kind: RecordKind
    source_event_id: str | None = None
    event_time: datetime | None = None
    receiver_id: str = Field(min_length=1)
    decoder: dict[str, str | None]
    message: dict[str, Any]


def normalize_icao(value: str) -> str:
    normalized = value.strip().upper()
    if not re.fullmatch(r"[0-9A-F]{6}", normalized):
        raise ValueError("ICAO24 must contain six hexadecimal characters")
    return normalized


def parse_time(value: str, name: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be an RFC3339 timestamp with timezone") from None


def validate_measurements(message: dict[str, Any]) -> dict[str, Any]:
    """Reject invalid numeric input; never coerce invalid values to zero."""
    result = dict(message)
    if "icao24" not in result:
        raise ValueError("icao24 is required")
    result["icao24"] = normalize_icao(str(result["icao24"]))
    for field in ("latitude_deg", "longitude_deg", "altitude_ft", "ground_speed_kt", "track_deg", "vertical_rate_fpm", "signal_metric"):
        value = result.get(field)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field} must be a finite number or null")
            result[field] = float(value)
    lat, lon = result.get("latitude_deg"), result.get("longitude_deg")
    if (lat is None) != (lon is None):
        raise ValueError("latitude and longitude must both be present or null")
    if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("coordinates are outside valid ranges")
    if result.get("track_deg") is not None and not 0 <= result["track_deg"] < 360:
        raise ValueError("track_deg must be in [0, 360)")
    return result
