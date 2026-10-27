"""TCP JSON adapter for readsb aircraft position updates."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
from typing import Any
from urllib.parse import urlparse

from .contracts import normalize_icao, validate_measurements


MAX_LINE_BYTES = 65536


class _ReceiverRegistrationError(Exception):
    pass


def _number(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number or null")
    return float(value)


def parse_readsb_line(line: bytes, *, receiver_id: str, decoder_version: str | None = None) -> dict[str, Any]:
    """Map one documented readsb JSON position line to one v1 observation."""
    try:
        aircraft = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("invalid_json") from None
    if not isinstance(aircraft, dict):
        raise ValueError("invalid_record")
    raw_hex = aircraft.get("hex")
    if not isinstance(raw_hex, str) or raw_hex.startswith("~"):
        raise ValueError("non_icao_address")
    try:
        icao24 = normalize_icao(raw_hex)
    except ValueError:
        raise ValueError("invalid_icao24") from None

    now = _number(aircraft.get("now"), "now")
    seen_pos = _number(aircraft.get("seen_pos"), "seen_pos")
    event_time = None
    if now is not None and seen_pos is not None and seen_pos >= 0:
        event_time = datetime.fromtimestamp(now - seen_pos, timezone.utc)

    altitude = aircraft.get("alt_baro")
    on_ground = None
    if isinstance(altitude, str):
        if altitude.lower() == "ground":
            on_ground = True
        altitude = None
    else:
        altitude = _number(altitude, "alt_baro")

    callsign = aircraft.get("flight")
    if callsign is not None and not isinstance(callsign, str):
        raise ValueError("invalid_flight")
    callsign = callsign.strip()[:16] or None if callsign else None
    squawk = aircraft.get("squawk")
    if squawk is not None and not isinstance(squawk, str):
        raise ValueError("invalid_squawk")
    if squawk:
        squawk = squawk[:8]

    values = validate_measurements({
        "icao24": icao24,
        "latitude_deg": _number(aircraft.get("lat"), "lat"),
        "longitude_deg": _number(aircraft.get("lon"), "lon"),
        "altitude_ft": altitude,
        "ground_speed_kt": _number(aircraft.get("gs"), "gs"),
        "track_deg": _number(aircraft.get("track"), "track"),
        "vertical_rate_fpm": _number(aircraft.get("baro_rate"), "baro_rate"),
        "signal_metric": _number(aircraft.get("rssi"), "rssi"),
    })
    values.update({
        "record_kind": "aircraft_update",
        "receiver_id": receiver_id,
        "event_time": event_time,
        "source_event_id": None,
        "callsign": callsign,
        "squawk": squawk,
        "on_ground": on_ground,
        "signal_metric_kind": "rssi" if aircraft.get("rssi") is not None else None,
        "signal_metric_unit": "dBFS" if aircraft.get("rssi") is not None else None,
        "decoder_name": "readsb",
        "decoder_version": decoder_version,
        "metadata": {"readsb_type": aircraft.get("type"), "messages": aircraft.get("messages")},
    })
    return values


class ReadsbIngestor:
    """Reconnectable line reader; DB calls run in a worker thread."""

    def __init__(self, endpoint: str, receiver_id: str, decoder_version: str | None, repository):
        parsed = urlparse(endpoint)
        self.endpoint = endpoint
        self.host = parsed.hostname or ""
        self.port = parsed.port or 0
        self.receiver_id = receiver_id
        self.decoder_version = decoder_version
        self.repository = repository
        self.receiver_registered = False
        self.connected = False
        self.last_message_at: datetime | None = None
        self.last_persisted_at: datetime | None = None
        self.accepted_count = 0
        self.rejected_count = 0
        self.reconnect_attempts = 0
        self.last_error_code: str | None = None
        self._stop = asyncio.Event()

    def stop(self):
        self._stop.set()

    def status(self) -> tuple[str, str | None]:
        if not self.connected:
            return "offline", self.last_error_code or "decoder_unavailable"
        if self.last_error_code == "database_unavailable":
            return "degraded", self.last_error_code
        if self.last_message_at is None or (datetime.now(timezone.utc) - self.last_message_at).total_seconds() > 120:
            return "degraded", "decoder_stale"
        return "online", None

    async def run(self):
        delay = 1.0
        while not self._stop.is_set():
            writer = None
            try:
                if not self.receiver_registered:
                    try:
                        await asyncio.to_thread(self.repository.ensure_receiver, self.receiver_id, {
                            "receiver_mode": "rtlsdr_usb", "decoder": "readsb",
                            "input_mode": "direct_usb", "output_mode": "readsb_json",
                            "endpoint": self.endpoint,
                        })
                        self.receiver_registered = True
                    except Exception:
                        raise _ReceiverRegistrationError from None
                reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=5)
                self.connected = True
                self.last_error_code = None
                delay = 1.0
                while not self._stop.is_set():
                    line = await asyncio.wait_for(reader.readline(), timeout=90)
                    if not line:
                        raise ConnectionError("decoder_closed")
                    if len(line) > MAX_LINE_BYTES:
                        self.rejected_count += 1
                        self.last_error_code = "decoder_record_too_large"
                        continue
                    try:
                        observation = parse_readsb_line(line, receiver_id=self.receiver_id, decoder_version=self.decoder_version)
                    except (ValueError, OverflowError):
                        self.rejected_count += 1
                        self.last_message_at = datetime.now(timezone.utc)
                        self.last_error_code = "decoder_record_invalid"
                        continue
                    self.last_message_at = datetime.now(timezone.utc)
                    try:
                        await asyncio.to_thread(self.repository.persist_observation, observation)
                    except Exception:
                        self.receiver_registered = False
                        self.last_error_code = "database_unavailable"
                        continue
                    self.accepted_count += 1
                    self.last_persisted_at = datetime.now(timezone.utc)
                    self.last_error_code = None
            except asyncio.CancelledError:
                raise
            except _ReceiverRegistrationError:
                self.connected = False
                self.reconnect_attempts += 1
                self.last_error_code = "database_unavailable"
            except Exception:
                self.connected = False
                self.reconnect_attempts += 1
                self.last_error_code = "decoder_unavailable"
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
            if not self._stop.is_set():
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                delay = min(delay * 2, 15.0)
