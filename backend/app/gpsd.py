"""Reconnectable GPSD JSON client for the receiver site's live position."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
from urllib.parse import urlparse


class GPSDMonitor:
    def __init__(self, endpoint: str):
        parsed = urlparse(endpoint if "://" in endpoint else f"tcp://{endpoint}")
        self.host = parsed.hostname or "gpsd"
        self.port = parsed.port or 2947
        self._stop = asyncio.Event()
        self._state = {
            "state": "offline", "latitude": None, "longitude": None,
            "accuracy_m": None, "altitude_m": None, "fix_mode": 0,
            "satellites_visible": 0, "satellites_used": 0,
            "fix_time": None, "updated_at": None,
        }

    def stop(self):
        self._stop.set()

    def snapshot(self) -> dict:
        return dict(self._state)

    async def run(self):
        delay = 1.0
        while not self._stop.is_set():
            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=5
                )
                writer.write(b'?WATCH={"enable":true,"json":true};\n')
                await writer.drain()
                delay = 1.0
                while not self._stop.is_set():
                    line = await asyncio.wait_for(reader.readline(), timeout=30)
                    if not line:
                        raise ConnectionError("gpsd_closed")
                    try:
                        message = json.loads(line)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if not isinstance(message, dict):
                        continue
                    if message.get("class") == "TPV":
                        self._update_tpv(message)
                    elif message.get("class") == "SKY":
                        satellites = message.get("satellites")
                        if isinstance(satellites, list):
                            self._state["satellites_visible"] = len(satellites)
                            self._state["satellites_used"] = sum(
                                1 for satellite in satellites
                                if isinstance(satellite, dict) and satellite.get("used") is True
                            )
                            self._state["updated_at"] = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                raise
            except Exception:
                self._state["state"] = "offline"
                self._state["latitude"] = None
                self._state["longitude"] = None
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

    def _update_tpv(self, message: dict):
        raw_mode = message.get("mode", 0)
        mode = raw_mode if isinstance(raw_mode, int) and raw_mode in (0, 1, 2, 3) else 0
        latitude = message.get("lat")
        longitude = message.get("lon")
        valid_position = (
            mode >= 2
            and isinstance(latitude, (int, float)) and not isinstance(latitude, bool)
            and isinstance(longitude, (int, float)) and not isinstance(longitude, bool)
            and math.isfinite(latitude) and math.isfinite(longitude)
            and -90 <= latitude <= 90 and -180 <= longitude <= 180
        )
        self._state.update({
            "state": "online" if valid_position else "no_fix",
            "latitude": float(latitude) if valid_position else None,
            "longitude": float(longitude) if valid_position else None,
            "accuracy_m": self._finite(message.get("epx")),
            "altitude_m": self._finite(message.get("alt")),
            "fix_mode": mode,
            "fix_time": message.get("time") if isinstance(message.get("time"), str) else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    @staticmethod
    def _finite(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
        return None
