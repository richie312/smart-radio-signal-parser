"""Environment settings. Secrets are never included in repr or errors."""
from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    operating_mode: str
    mysql: dict = field(repr=False)
    config_errors: tuple[str, ...] = ()

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
            # Until receiver and decoder compatibility is approved, configuration remains a hard gate.
            for key in ("RECEIVER_MODE", "DECODER_NAME", "DECODER_INPUT_MODE", "DECODER_OUTPUT_MODE"):
                if not os.getenv(key): errors.append(f"{key} is required in adsb mode")
        if mode == "production":
            for key in ("API_BIND_HOST", "API_PORT", "CORS_ORIGINS", "FLIGHT_SESSION_SILENCE_SECONDS", "AIRCRAFT_STALE_AFTER_SECONDS", "OBSERVATION_RETENTION_DAYS"):
                if not os.getenv(key): errors.append(f"{key} is required in production")
        return cls(env or "", os.getenv("LOG_LEVEL", "INFO"), mode or "", mysql, tuple(errors))
