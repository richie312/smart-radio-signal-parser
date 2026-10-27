-- MySQL 8+ schema. Apply explicitly with an operator-provisioned migration account.
-- The application never applies DDL during startup.
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INT NOT NULL PRIMARY KEY,
  applied_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))
) ENGINE=InnoDB;

CREATE TABLE receivers (
  receiver_id VARCHAR(96) NOT NULL PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  receiver_type VARCHAR(64) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  configuration_json JSON NOT NULL,
  latitude_deg DECIMAL(9,6) NULL,
  longitude_deg DECIMAL(9,6) NULL,
  location_label VARCHAR(255) NULL,
  created_at DATETIME(3) NOT NULL,
  updated_at DATETIME(3) NOT NULL,
  CONSTRAINT chk_receiver_lat CHECK (latitude_deg IS NULL OR latitude_deg BETWEEN -90 AND 90),
  CONSTRAINT chk_receiver_lon CHECK (longitude_deg IS NULL OR longitude_deg BETWEEN -180 AND 180)
) ENGINE=InnoDB;

CREATE TABLE aircraft (
  icao24 CHAR(6) NOT NULL PRIMARY KEY,
  first_seen_at DATETIME(3) NOT NULL,
  last_seen_at DATETIME(3) NOT NULL,
  last_callsign VARCHAR(16) NULL,
  last_squawk VARCHAR(8) NULL,
  created_at DATETIME(3) NOT NULL,
  updated_at DATETIME(3) NOT NULL,
  CONSTRAINT chk_aircraft_icao CHECK (icao24 REGEXP '^[0-9A-F]{6}$')
) ENGINE=InnoDB;

CREATE TABLE aircraft_observations (
  observation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  record_kind ENUM('decoded_frame','aircraft_update') NOT NULL,
  icao24 CHAR(6) NOT NULL,
  receiver_id VARCHAR(96) NOT NULL,
  event_time DATETIME(3) NULL,
  ingested_at DATETIME(3) NOT NULL,
  source_event_id VARCHAR(255) NULL,
  callsign VARCHAR(16) NULL,
  latitude_deg DECIMAL(10,7) NULL,
  longitude_deg DECIMAL(10,7) NULL,
  altitude_ft DOUBLE NULL,
  ground_speed_kt DOUBLE NULL,
  track_deg DOUBLE NULL,
  vertical_rate_fpm DOUBLE NULL,
  squawk VARCHAR(8) NULL,
  on_ground BOOLEAN NULL,
  signal_metric DOUBLE NULL,
  signal_metric_kind VARCHAR(64) NULL,
  signal_metric_unit VARCHAR(32) NULL,
  decoder_name VARCHAR(96) NOT NULL,
  decoder_version VARCHAR(96) NULL,
  metadata_json JSON NOT NULL,
  UNIQUE KEY uq_observation_source (receiver_id, decoder_name, source_event_id),
  KEY ix_observation_aircraft_time (icao24,event_time,observation_id),
  KEY ix_observation_receiver_ingested (receiver_id,ingested_at),
  KEY ix_observation_ingested (ingested_at),
  CONSTRAINT fk_observation_aircraft FOREIGN KEY (icao24) REFERENCES aircraft(icao24),
  CONSTRAINT fk_observation_receiver FOREIGN KEY (receiver_id) REFERENCES receivers(receiver_id),
  CONSTRAINT chk_observation_lat CHECK (latitude_deg IS NULL OR latitude_deg BETWEEN -90 AND 90),
  CONSTRAINT chk_observation_lon CHECK (longitude_deg IS NULL OR longitude_deg BETWEEN -180 AND 180)
) ENGINE=InnoDB;

CREATE TABLE flight_sessions (
  session_id CHAR(36) NOT NULL PRIMARY KEY,
  icao24 CHAR(6) NOT NULL,
  receiver_id VARCHAR(96) NOT NULL,
  started_at DATETIME(3) NOT NULL,
  last_observed_at DATETIME(3) NOT NULL,
  ended_at DATETIME(3) NULL,
  first_observation_id BIGINT UNSIGNED NOT NULL,
  last_observation_id BIGINT UNSIGNED NOT NULL,
  callsign VARCHAR(16) NULL,
  minimum_distance_m DOUBLE NULL,
  minimum_distance_observation_id BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL,
  updated_at DATETIME(3) NOT NULL,
  KEY ix_sessions_aircraft_started (icao24,started_at,session_id),
  KEY ix_sessions_receiver (receiver_id,started_at),
  CONSTRAINT fk_session_aircraft FOREIGN KEY (icao24) REFERENCES aircraft(icao24),
  CONSTRAINT fk_session_receiver FOREIGN KEY (receiver_id) REFERENCES receivers(receiver_id),
  CONSTRAINT fk_session_first_obs FOREIGN KEY (first_observation_id) REFERENCES aircraft_observations(observation_id),
  CONSTRAINT fk_session_last_obs FOREIGN KEY (last_observation_id) REFERENCES aircraft_observations(observation_id),
  CONSTRAINT fk_session_min_obs FOREIGN KEY (minimum_distance_observation_id) REFERENCES aircraft_observations(observation_id)
) ENGINE=InnoDB;

CREATE TABLE enrichment_cache (
  cache_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  icao24 CHAR(6) NOT NULL,
  provider_id VARCHAR(96) NOT NULL,
  data_kind ENUM('image','flight') NOT NULL,
  lookup_key VARCHAR(255) NOT NULL,
  payload_json JSON NULL,
  attribution_json JSON NULL,
  fetched_at DATETIME(3) NULL,
  expires_at DATETIME(3) NULL,
  status VARCHAR(32) NOT NULL,
  last_error_code VARCHAR(96) NULL,
  UNIQUE KEY uq_enrichment_lookup (provider_id,data_kind,lookup_key),
  KEY ix_enrichment_expiry (expires_at),
  KEY ix_enrichment_icao (icao24),
  CONSTRAINT fk_enrichment_aircraft FOREIGN KEY (icao24) REFERENCES aircraft(icao24)
) ENGINE=InnoDB;

CREATE TABLE ingestion_health (
  health_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  receiver_id VARCHAR(96) NULL,
  component VARCHAR(32) NOT NULL,
  state ENUM('online','degraded','offline','unconfigured','error') NOT NULL,
  changed_at DATETIME(3) NOT NULL,
  last_success_at DATETIME(3) NULL,
  last_message_at DATETIME(3) NULL,
  reconnect_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
  messages_seen BIGINT UNSIGNED NOT NULL DEFAULT 0,
  messages_rejected BIGINT UNSIGNED NOT NULL DEFAULT 0,
  error_code VARCHAR(96) NULL,
  diagnostic_json JSON NULL,
  KEY ix_health_receiver_changed (receiver_id,changed_at),
  CONSTRAINT fk_health_receiver FOREIGN KEY (receiver_id) REFERENCES receivers(receiver_id)
) ENGINE=InnoDB;

INSERT INTO schema_migrations(version) VALUES (1);
