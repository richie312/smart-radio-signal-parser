"""Repository boundary and MySQL implementation (never migrates on startup)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import json
from typing import Any


class Repository(ABC):
    @abstractmethod
    def check_ready(self) -> tuple[bool, str | None]: ...

    @abstractmethod
    def list_aircraft(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_aircraft(self, icao24: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def observations(self, icao24: str, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def sessions(self, icao24: str, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def analytics(self, **filters: Any) -> dict[str, Any]: ...


class MySQLRepository(Repository):
    """mysql-connector implementation; caller supplies already-provisioned DB config."""
    EXPECTED_SCHEMA_VERSION = 1

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def _connect(self):
        import mysql.connector
        return mysql.connector.connect(**self.config)

    def check_ready(self) -> tuple[bool, str | None]:
        try:
            connection = self._connect()
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
                row = cursor.fetchone()
                if not row or int(row[0]) != self.EXPECTED_SCHEMA_VERSION:
                    return False, "schema_incompatible"
                return True, None
            finally:
                connection.close()
        except Exception:
            return False, "database_unavailable"

    def _query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            connection.close()

    def list_aircraft(self, **filters):
        # Aircraft snapshot is projected from the latest observation; stable ordering.
        sql = """SELECT a.icao24,a.first_seen_at,a.last_seen_at,o.* FROM aircraft a
                 JOIN aircraft_observations o ON o.observation_id=(SELECT o2.observation_id FROM aircraft_observations o2 WHERE o2.icao24=a.icao24 ORDER BY COALESCE(o2.event_time,o2.ingested_at) DESC,o2.observation_id DESC LIMIT 1)
                 WHERE (%s IS NULL OR UPPER(TRIM(o.callsign))=UPPER(%s)) AND (%s IS NULL OR a.icao24=%s)
                 AND (%s IS NULL OR o.altitude_ft >= %s) AND (%s IS NULL OR o.altitude_ft <= %s)
                 AND (%s IS NULL OR a.last_seen_at >= %s) ORDER BY a.last_seen_at DESC,a.icao24 ASC LIMIT %s"""
        return self._query(sql, (filters.get("callsign"), filters.get("callsign"), filters.get("icao24"), filters.get("icao24"), filters.get("altitude_min_ft"), filters.get("altitude_min_ft"), filters.get("altitude_max_ft"), filters.get("altitude_max_ft"), filters.get("seen_since"), filters.get("seen_since"), filters.get("limit", 50)))

    def get_aircraft(self, icao24):
        rows = self._query("SELECT a.icao24,a.first_seen_at,a.last_seen_at,o.* FROM aircraft a JOIN aircraft_observations o ON o.observation_id=(SELECT observation_id FROM aircraft_observations WHERE icao24=a.icao24 ORDER BY COALESCE(event_time,ingested_at) DESC,observation_id DESC LIMIT 1) WHERE a.icao24=%s", (icao24,))
        return rows[0] if rows else None

    def observations(self, icao24, **filters):
        sql = "SELECT * FROM aircraft_observations WHERE icao24=%s"
        params: list[Any] = [icao24]
        if filters.get("from"):
            sql += " AND event_time >= %s"; params.append(filters["from"])
        if filters.get("to"):
            sql += " AND event_time < %s"; params.append(filters["to"])
        sql += " ORDER BY event_time ASC,observation_id ASC LIMIT %s"; params.append(filters.get("limit", 50))
        return self._query(sql, tuple(params))

    def sessions(self, icao24, **filters):
        sql = "SELECT * FROM flight_sessions WHERE icao24=%s"; params: list[Any] = [icao24]
        if filters.get("from"):
            sql += " AND started_at >= %s"; params.append(filters["from"])
        if filters.get("to"):
            sql += " AND started_at < %s"; params.append(filters["to"])
        sql += " ORDER BY started_at ASC,session_id ASC LIMIT %s"; params.append(filters.get("limit", 50))
        return self._query(sql, tuple(params))

    def analytics(self, **filters):
        rows = self._query("SELECT COUNT(DISTINCT icao24) aircraft_count,COUNT(*) observation_count,SUM(record_kind='decoded_frame') frame_count,SUM(record_kind='aircraft_update') update_count,SUM(latitude_deg IS NOT NULL AND longitude_deg IS NOT NULL) position_count FROM aircraft_observations WHERE ingested_at >= %s AND ingested_at < %s", (filters["from"], filters["to"]))
        return rows[0] if rows else {}


class EmptyRepository(Repository):
    """Explicit test/mock repository. Empty results are data_available=false, never live data."""
    def check_ready(self): return True, None
    def list_aircraft(self, **filters): return []
    def get_aircraft(self, icao24): return None
    def observations(self, icao24, **filters): return []
    def sessions(self, icao24, **filters): return []
    def analytics(self, **filters): return {"aircraft_count": 0, "observation_count": 0, "frame_count": None, "update_count": 0, "position_count": 0}
