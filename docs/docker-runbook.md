# Docker build and runbook

Run commands from the repository root, where `docker-compose.yaml` is located. On Linux, Compose builds the local readsb wrapper image from the pinned upstream RTL-SDR-enabled image and builds the ADS-B API image. Compose starts the two services on `my_rasp_network`; readsb receives the USB SDR and the API reads its JSON position stream at `readsb:30006`.

| Service | Build context | Purpose |
| --- | --- | --- |
| `readsb` | Repository root | Decodes ADS-B using the attached RTL-SDR and serves JSON positions inside the Compose network. |
| `adsb_api` | `backend/` | Runs the FastAPI application and persists observations to MySQL. |

The readsb base image is pinned in the root `Dockerfile`. It supports common `amd64` and `arm64` Linux Docker hosts; the Linux host must expose the dongle at `/dev/bus/usb`.

## Prepare configuration

Create `.env` from the example, then set the database account and enable ADS-B mode:

```sh
cp .env.example .env
```

Set the ADS-B values in `.env`:

```dotenv
OPERATING_MODE=adsb
DB_NAME=adsb
DB_USER=<provisioned runtime user>
DB_PASSWORD=<runtime password>
RECEIVER_ID=adsb-node-10
RECEIVER_MODE=rtlsdr_usb
DECODER_NAME=readsb
DECODER_INPUT_MODE=direct_usb
DECODER_OUTPUT_MODE=readsb_json
DECODER_ENDPOINT=tcp://readsb:30006
```

Keep `.env` local and do not commit credentials. The migration/admin account should remain separate from the runtime database account. The runtime account needs `SELECT, INSERT, UPDATE` on `receivers` and `aircraft`, and `SELECT, INSERT` on `aircraft_observations`, plus the API's read access to the schema.

Create the external Compose network once on each Docker host if it is not already present:

```sh
docker network inspect my_rasp_network || docker network create my_rasp_network
```

## Switch an existing .10 installation to containerized readsb

Only one process can own the USB SDR. This project previously used host-installed readsb and may have an old `rtl_tcp` container. Update `.env` so `DECODER_ENDPOINT=tcp://readsb:30006`, then stop those owners before starting the Compose readsb service:

```sh
sudo systemctl disable --now readsb
docker rm -f rtl_tcp
sudo fuser -v /dev/bus/usb/*
```

If Docker says there is no `rtl_tcp` container, continue. The last command should show no process using the dongle. If it still lists a process, identify and stop that owner before continuing. The `disable` command prevents host readsb from automatically competing with the Compose service after a reboot. To roll back to host readsb, stop the Compose `readsb` service first, then run `sudo systemctl enable --now readsb`.

## Build images

Build all configured services without starting containers:

```sh
docker-compose build
```

Build or refresh one service:

```sh
docker-compose build readsb
docker-compose build adsb_api
```

Pull current bases before building, or rebuild without cache:

```sh
docker-compose build --pull
docker-compose build --no-cache
```

The readsb base image is intentionally pinned; `--pull` will not change its pinned version. Upgrade the tag in `Dockerfile` as a deliberate change.

## Start and verify

Build and start both decoder and API:

```sh
docker-compose up -d --build --remove-orphans readsb adsb_api
docker-compose ps
docker-compose logs --tail=80 readsb adsb_api
```

Check API readiness and component status:

```sh
python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/ready', timeout=5).status)"
python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/api/v1/status', timeout=5).read().decode())"
```

Readiness should be `200`. Once readsb receives aircraft positions and the API writes them to MySQL, status should show the receiver, decoder, and ingestion online with an increasing accepted count. These JSON lines are aircraft position updates, not individual RF frames, so decoded frame rate is not available from this output.

The API binds to `127.0.0.1:8010` on the Docker host. To view the .10 API from a workstation React dev server, create an SSH tunnel using the configured host alias:

```powershell
ssh -N -L 18010:127.0.0.1:8010 adsb-node-10
```

Then start Vite with the tunnel as its API target:

```powershell
$env:VITE_DEV_API_TARGET = 'http://127.0.0.1:18010'
npm.cmd run dev -- --host 127.0.0.1
```

## Stop and restart

```sh
docker-compose restart readsb adsb_api
docker-compose logs -f readsb
docker-compose logs -f adsb_api
docker-compose stop adsb_api
docker-compose stop readsb
```

`docker-compose down` removes this project's containers but leaves the external `my_rasp_network` and the separately managed MySQL database intact. Do not run host readsb while the Compose `readsb` service owns the dongle.

## Troubleshooting

### Compose reports that `my_rasp_network` is missing

Create the external network on this Docker host:

```sh
docker network create my_rasp_network
```

### readsb cannot open the RTL-SDR

Check that the host has the device and no other process owns it:

```sh
lsusb
sudo fuser -v /dev/bus/usb/*
docker-compose logs --tail=80 readsb
```

Stop competing host readsb, `rtl_tcp`, or other SDR services before restarting the Compose readsb container.

### API reports `database_unavailable`

Check the configured database name, network reachability, credentials, and table grants. Error 1049 means the database name does not exist; error 1045 means MySQL rejected the credentials or client host. Apply `backend/migrations/001_initial.sql` to the existing `adsb` schema using an authorized migration/admin account, then verify that `schema_migrations` contains version 1. Do not enable remote MySQL root access just to run the API.

### Legacy Compose fails with `KeyError: 'ContainerConfig'`

With Docker Compose V1, remove and recreate only the affected service container:

```sh
docker-compose rm -sf adsb_api
docker-compose up -d --build adsb_api
```

For the decoder container, use `readsb` as the service name. Do not remove the USB-owning readsb service unless you intend to stop reception.
