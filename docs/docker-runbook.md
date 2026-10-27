# Docker build and runbook

Run these commands from the repository root, where `docker-compose.yaml` is located. Docker Compose builds two images:

| Service | Build context | Dockerfile | Purpose |
| --- | --- | --- | --- |
| `rtl_tcp` | Repository root | `Dockerfile` | Exposes raw RTL-SDR control/IQ data on port 1234. Requires a Linux Docker host with the SDR attached over USB. |
| `adsb_api` | `backend/` | `backend/Dockerfile` | Runs the FastAPI application. It does not own the SDR or decode radio signals. |

## Prepare the API configuration

Create `.env` from the example, then fill in the provisioned database account and schema values:

```powershell
Copy-Item .env.example .env
```

```sh
cp .env.example .env
```

The Compose service requires a valid `.env`, the existing external `my_rasp_network`, and verified database settings before it can start successfully. `.env` is ignored by Git. Leave `OPERATING_MODE=sdrpp_scanner` unless ADS-B receiver ownership and decoder configuration on `.10` have been verified. Do not commit credentials.

On each Docker host, check whether the external network exists:

```sh
docker network inspect my_rasp_network
```

If Docker reports that the network does not exist, create it once on that host, then retry Compose:

```sh
docker network create my_rasp_network
docker-compose up -d adsb_api
```

This creates only the Docker bridge network; it does not create a database or change database credentials. If another service manages the intended network, use that service's network configuration instead of creating a duplicate.

## Build images

Build every image defined in Compose without starting containers:

```sh
docker compose build
```

Build one service at a time:

```sh
docker compose build rtl_tcp
docker compose build adsb_api
```

Pull newer base images while building, or rebuild without using cached layers:

```sh
docker compose build --pull
docker compose build --no-cache
```

Apply either option to one service by adding its name, for example:

```sh
docker compose build --pull adsb_api
docker compose build --no-cache adsb_api
```

Equivalent direct Docker builds, when you need to build outside Compose, are:

```sh
docker build -f Dockerfile -t smart-radio-rtl-tcp:local .
docker build -f backend/Dockerfile -t smart-radio-adsb-api:local ./backend
```

Compose uses its own project image names when it builds services. Use the Compose commands for the normal run workflow so it starts the image built from the matching service configuration.

## Start services

Start only the API after `.env` and the external network are ready:

```sh
docker compose up --build -d adsb_api
```

Start the raw RTL-SDR service on the Linux host that physically owns the dongle:

```sh
docker compose up --build -d rtl_tcp
```

Start both Compose services only when that is the intended receiver mode and the USB ownership procedure has been verified:

```sh
docker compose up --build -d
```

The `rtl_tcp` service maps `/dev/bus/usb` and uses host networking. It will not run as configured on a standard Windows Docker Desktop host. Its output is raw IQ/control data, not decoded ADS-B. Do not treat it as the `.10` decoder or run competing SDR owners against the same dongle.

The API publishes `127.0.0.1:8010` on the Docker host and attaches to the external `my_rasp_network`. It does not create a database or decoder service.

## Enable readsb aircraft updates

The API can consume readsb's TCP JSON position output from the receiver host. Each line is stored as an `aircraft_update`; frame counts/rates remain unavailable because these lines are position updates, not individual RF frames.

On `.10`, first choose a TCP port that `ss -ltn` shows is unused. Stop the current RTL-SDR owner only when you are ready to switch modes, then confirm it released the dongle. Run readsb in the foreground for the initial check, using the selected free port in place of `<JSON_PORT>`:

```sh
docker-compose stop rtl_tcp
docker-compose ps
sudo fuser -v /dev/bus/usb/*
readsb --quiet --net --device-type rtlsdr --freq 1090000000 --gain auto --net-bind-address 192.168.1.10 --net-json-port <JSON_PORT>
```

Keep readsb running while completing the API checks. Confirm it acquired the expected RTL-SDR and is emitting JSON position lines. Do not start it if `fuser` shows another SDR process still owns the device. Stop the foreground process with Ctrl+C to release the device during rollback.

After selecting the port, set these values in `.10`'s `.env`:

```dotenv
OPERATING_MODE=adsb
RECEIVER_ID=adsb-node-10
RECEIVER_MODE=rtlsdr_usb
DECODER_NAME=readsb
DECODER_INPUT_MODE=direct_usb
DECODER_OUTPUT_MODE=readsb_json
DECODER_ENDPOINT=tcp://192.168.1.10:<JSON_PORT>
```

Replace `<JSON_PORT>` with the actual selected number; angle brackets are not valid in the value. Keep the existing database settings. The application creates/updates the receiver configuration row and writes aircraft observations, so its MySQL account needs `SELECT, INSERT, UPDATE` on `receivers` and `aircraft`, and `SELECT, INSERT` on `aircraft_observations`, in addition to the read access needed by the API. Keep schema migration privileges separate.

Restart the API container after saving `.env`:

```sh
docker-compose up -d --build adsb_api
docker-compose logs --tail=80 adsb_api
python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/ready', timeout=5).status)"
python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/api/v1/status', timeout=5).read().decode())"
```

Readiness should be `200`. Once valid position lines are received and committed, status should show the receiver, decoder, and ingestion online with an accepted count. If the database is ready but ingestion reports `database_unavailable`, check the runtime account's table permissions and the API logs. The dashboard refreshes its aircraft list automatically.

To view the `.10` API from a local React dev server without colliding with a local API on port 8010, create an SSH tunnel on the workstation using the configured `.10` SSH alias:

```powershell
ssh -N -L 18010:127.0.0.1:8010 adsb-node-10
```

Then start Vite with its API proxy pointed through that tunnel:

```powershell
$env:VITE_DEV_API_TARGET = 'http://127.0.0.1:18010'
npm.cmd run dev -- --host 127.0.0.1
```

## Check and stop services

```sh
docker compose ps
docker compose logs -f adsb_api
docker compose logs -f rtl_tcp
```

Stop one service or all services in this Compose project:

```sh
docker compose stop adsb_api
docker compose stop rtl_tcp
docker compose down
```

`docker compose down` removes this project's containers and its Compose-managed resources. The declared external `my_rasp_network` is not removed.

## API container restarts with a configuration error

If `docker-compose ps` shows `adsb-api` as `Restarting` and its logs report `required configuration is missing or invalid`, stop the restart loop and check the local `.env` file. The required base values are `APP_ENV`, `OPERATING_MODE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`. `APP_ENV` must be `development`, `test`, or `production`; `OPERATING_MODE` must be `adsb` or `sdrpp_scanner`; `DB_PORT` must be a valid TCP port. When `OPERATING_MODE=adsb`, also configure `RECEIVER_MODE`, `DECODER_NAME`, `DECODER_INPUT_MODE`, and `DECODER_OUTPUT_MODE` after the receiver/decoder path is verified.

```sh
docker-compose stop adsb_api
grep -nE '^(DB_NAME|DB_USER|DB_PASSWORD)=$' .env
nano .env
docker-compose up -d --build adsb_api
docker-compose logs --tail=50 adsb_api
```

The `grep` command reports only exactly empty database fields; it does not print populated credentials. Do not paste `.env` contents into logs or chat. Once configuration validation passes, a database connection or schema problem will appear separately in readiness/log output.

## Readiness reports `database_unavailable` with MySQL error 1049

MySQL error 1049 means the configured database name was not found on the server. Confirm `DB_NAME` in `.env` (this deployment uses `adsb`), then create that schema on the existing MySQL server and apply the migration once. The migration creates tables inside the selected schema; it does not create the schema itself. Use an authorized MySQL administrator/migration account; do not assume `root` is allowed to connect remotely. These commands prompt for the MySQL password rather than placing it in shell history:

```sh
read -rp "MySQL administrator username: " DB_ADMIN_USER
mysql -h 192.168.1.50 -u "$DB_ADMIN_USER" -p -e "CREATE DATABASE IF NOT EXISTS adsb CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
mysql -h 192.168.1.50 -u "$DB_ADMIN_USER" -p adsb < backend/migrations/001_initial.sql
```

Run them from the repository root on a host with the MySQL client installed, or run the equivalent SQL in an approved MySQL administration session. Apply the migration only once to an empty `adsb` schema; it contains table creation statements that are not all repeatable. Afterward, check readiness again. If error 1049 persists, the running container is using a different `DB_NAME` or `.env` than expected.

On Ubuntu/Debian, if the `mysql` command is missing, install the MySQL 8 client tools first:

```sh
sudo apt update
sudo apt install mysql-client-core-8.0
```

## MySQL returns error 1045 for `root`

Error 1045 means MySQL rejected the credentials or does not allow that account from the client host. In this deployment the server reports the client as `192.168.1.10`. Do not enable remote root login just to run the API. Use an approved MySQL administration session on `.50` to create the `adsb` schema and apply the migration, then provision a dedicated runtime account allowed from `.10` with only the required schema privileges. Set that account and its password in the `.10` `.env` as `DB_USER` and `DB_PASSWORD`; keep the migration/admin account separate.

## MySQL returns error 1146 for `schema_migrations`

Error 1146 means the API connected to a database but the `schema_migrations` table is missing in the selected schema. Confirm the container's `DB_NAME` is `adsb`, then inspect `SHOW TABLES` in that schema using an authorized migration/admin session. If the schema is empty, apply the corrected `backend/migrations/001_initial.sql` once. If any migration tables already exist, do not rerun the full file: several `CREATE TABLE` statements are not idempotent, so inspect the partial state first. A successful migration inserts version `1` into `schema_migrations`.

## `ContainerConfig` error from legacy Compose

The Python `docker-compose` 1.29.2 client can fail with `KeyError: 'ContainerConfig'` while recreating a container against a newer Docker Engine. Prefer the Compose V2 plugin (`docker compose`). If it is installed, remove only the stale API container and recreate it:

```sh
docker compose version
docker compose rm -sf adsb_api
docker compose up -d --build adsb_api
```

Removing the `adsb_api` service container removes only that container; this service has no data volumes, and the separately managed database is not affected. The Compose-generated container name may include a project prefix, so remove by service name instead of assuming it is exactly `adsb-api`. Do not use `docker-compose down` as a workaround if `rtl_tcp` must remain running, because that command stops the whole Compose project. If `docker compose` is unavailable, install the Compose V2 plugin for the host before retrying.

As a one-time workaround when only the legacy `docker-compose` command is installed, remove the stale API container and retry with that command:

```sh
docker-compose rm -sf adsb_api
docker-compose up -d --build adsb_api
```

This also removes only the API container, including when Compose assigned it a project-prefixed name. Upgrade to Compose V2 when practical; do not remove the `rtl_tcp` container to work around this API recreation error.
