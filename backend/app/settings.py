"""Environment settings. Secrets are never included in repr or errors."""
from dataclasses import dataclass, field
import os
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    operating_mode: str
    mysql: dict = field(repr=False)
    config_errors: tuple[str, ...] = ()
    receiver_id: str = ""
    decoder_endpoint: str = ""
    decoder_version: str | None = None
    radio_control_url: str = "http://radio-control:8090"
    radio_control_token: str = field(default="", repr=False)
    gpsd_endpoint: str = "gpsd:2947"

    @classmethod
    def from_env(cls):
        errors: list[str] = []
        env = os.getenv("APP_ENV")
        mode = os.getenv("OPERATING_MODE")
        if env not in {"development", "test", "production"}: errors.append("APP_ENV is required and must be development, test, or production")
        if mode not in {"adsb", "sdrpp_scanner"}: errors.append("OPERATING_MODE is required and must be adsb or sdrpp_scanner")
        mysql: dict = {}
        for key in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
            if not os.getenv(key): errors.append(f"{key} is required")
        if all(os.getenv(k) for k in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")):
            try: port = int(os.environ["DB_PORT"])
            except ValueError: port = 0
            if not 1 <= port <= 65535: errors.append("DB_PORT must be a valid TCP port")
            mysql = {"host": os.environ["DB_HOST"], "port": port, "database": os.environ["DB_NAME"], "user": os.environ["DB_USER"], "password": os.environ["DB_PASSWORD"], "connection_timeout": int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))}
        if mode == "adsb":
            for key in ("RECEIVER_ID", "RECEIVER_MODE", "DECODER_NAME", "DECODER_INPUT_MODE", "DECODER_OUTPUT_MODE", "DECODER_ENDPOINT"):
                if not os.getenv(key): errors.append(f"{key} is required in adsb mode")
            if not os.getenv("RADIO_CONTROL_TOKEN"): errors.append("RADIO_CONTROL_TOKEN is required in adsb mode")
            if os.getenv("RECEIVER_MODE") != "rtlsdr_usb": errors.append("RECEIVER_MODE must be rtlsdr_usb for the configured readsb adapter")
            if os.getenv("DECODER_NAME") != "readsb": errors.append("DECODER_NAME must be readsb for the configured adapter")
            if os.getenv("DECODER_INPUT_MODE") != "direct_usb": errors.append("DECODER_INPUT_MODE must be direct_usb for readsb")
            if os.getenv("DECODER_OUTPUT_MODE") != "readsb_json": errors.append("DECODER_OUTPUT_MODE must be readsb_json")
            endpoint = os.getenv("DECODER_ENDPOINT", "")
            if endpoint:
                parsed = urlparse(endpoint)
                try: endpoint_port = parsed.port
                except ValueError: endpoint_port = None
                if parsed.scheme != "tcp" or not parsed.hostname or endpoint_port is None or not 1 <= endpoint_port <= 65535:
                    errors.append("DECODER_ENDPOINT must use tcp://host:port format")
            if len(os.getenv("RECEIVER_ID", "")) > 96 or os.getenv("RECEIVER_ID", "").strip() != os.getenv("RECEIVER_ID", ""):
                errors.append("RECEIVER_ID must be at most 96 characters and have no surrounding whitespace")
        else:
            endpoint = ""
        if mode == "production":
            for key in ("API_BIND_HOST", "API_PORT", "CORS_ORIGINS", "FLIGHT_SESSION_SILENCE_SECONDS", "AIRCRAFT_STALE_AFTER_SECONDS", "OBSERVATION_RETENTION_DAYS"):
                if not os.getenv(key): errors.append(f"{key} is required in production")
        return cls(env or "", os.getenv("LOG_LEVEL", "INFO"), mode or "", mysql, tuple(errors),
                   os.getenv("RECEIVER_ID", ""), endpoint, os.getenv("DECODER_VERSION") or None,
                   os.getenv("RADIO_CONTROL_URL", "http://radio-control:8090"), os.getenv("RADIO_CONTROL_TOKEN", ""),
                   os.getenv("GPSD_ENDPOINT", "gpsd:2947"))
