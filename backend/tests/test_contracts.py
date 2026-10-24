"""Unit tests use explicit test inputs only; no fixture represents live reception."""
from datetime import datetime, timezone
import unittest

from app.contracts import normalize_icao, parse_time, validate_measurements


class ContractTests(unittest.TestCase):
    def test_icao_normalization(self):
        self.assertEqual(normalize_icao(" abc123 "), "ABC123")
        with self.assertRaises(ValueError): normalize_icao("ABC12Z")

    def test_null_is_not_zero_and_numeric_zero_is_valid(self):
        self.assertIsNone(validate_measurements({"icao24": "ABC123", "latitude_deg": None, "longitude_deg": None})["latitude_deg"])
        self.assertEqual(validate_measurements({"icao24": "ABC123", "latitude_deg": 0, "longitude_deg": 0})["latitude_deg"], 0.0)

    def test_invalid_coordinate_pair_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError): validate_measurements({"icao24": "ABC123", "latitude_deg": 0, "longitude_deg": None})
        with self.assertRaises(ValueError): validate_measurements({"icao24": "ABC123", "signal_metric": float("nan")})

    def test_rfc3339_requires_timezone(self):
        self.assertEqual(parse_time("2025-01-01T00:00:00Z", "from").tzinfo, timezone.utc)
        with self.assertRaises(ValueError): parse_time("2025-01-01T00:00:00", "from")


if __name__ == "__main__": unittest.main()
