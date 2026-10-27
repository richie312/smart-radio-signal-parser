"""API contract checks against an explicit empty test repository, never live data."""
import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories import EmptyRepository
from app.settings import Settings


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        cfg = Settings("test", "WARNING", "sdrpp_scanner", {}, ())
        self.client = TestClient(create_app(EmptyRepository(), cfg))

    def test_status_marks_scanner_mode_inactive(self):
        response = self.client.get("/api/v1/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["receiver"]["state"], "unconfigured")
        self.assertEqual(response.json()["receiver"]["details"]["reason"], "inactive_by_mode")

    def test_empty_snapshot_and_optional_features_are_truthful(self):
        self.assertEqual(self.client.get("/api/v1/aircraft").json(), {"items": [], "next_cursor": None})
        self.assertEqual(self.client.get("/api/v1/audio/config").json()["state"], "unconfigured")
        ts = self.client.get("/api/v1/analytics/timeseries", params={"from": "2025-01-01T00:00:00Z", "to": "2025-01-01T00:05:00Z", "bucket_seconds": 60}).json()
        self.assertIn("buckets", ts)
        self.assertFalse(ts["data_available"])

    def test_unknown_filter_uses_problem_contract(self):
        response = self.client.get("/api/v1/aircraft", params={"invented": "1"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"code", "message", "details", "request_id"})

    def test_websocket_event_envelope(self):
        with self.client.websocket_connect("/api/v1/stream") as ws:
            event = ws.receive_json()
            self.assertEqual(event["schema_version"], 1)
            self.assertEqual(event["event_type"], "status.updated")
            self.assertIn("event_time", event)


if __name__ == "__main__": unittest.main()
