# Docker build and runbook

Run commands from the repository root on `.10`. Compose builds a radio controller image, a GPSD sidecar, and the API image. The radio controller owns the RTL-SDR and runs exactly one receive process at a time: readsb for ADS-B, or rtl_fm plus FFmpeg for airband AM audio. The GPSD sidecar owns the VK-172 USB serial device and shares the live site fix with the API only on the Docker network. The API proxies browser audio and reads GPSD JSON; it has no USB device mapping or Docker socket.

| Service | Purpose |
| --- | --- |
| `radio_control` | Owns `/dev/bus/usb`; switches between readsb JSON output and one selected Hyderabad airband frequency. |
| `gpsd` | Reads the VK-172 USB GPS at `/dev/serial/by-id/...` and serves GPSD JSON privately on the Compose network. |
| `adsb_api` | Runs FastAPI, persists ADS-B observations, and provides authenticated internal radio control and audio proxy endpoints. |

The root `Dockerfile` uses a pinned upstream readsb image and adds RTL-SDR tools, FFmpeg, and the small receive-mode controller. The AAI eAIP provides the Hyderabad VOHS station presets in `backend/stations.json`.

## Configure `.env`

Create `.env` from the example if needed, then configure the provisioned database credentials and ADS-B receiver values:

```sh
cp .env.example .env
openssl rand -hex 32
```

Copy the generated token into `RADIO_CONTROL_TOKEN` in `.env`. Use this same `.env` value for `radio_control` and `adsb_api`; do not paste it into chat or commit it. Set the GPS serial path and dialout group ID to match `.10` (the current values are the detected VK-172 path and Ubuntu's `dialout` GID):

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
DECODER_ENDPOINT=tcp://radio-control:30006
GPS_DEVICE=/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00
GPS_DIALOUT_GID=20
```

Keep the migration/admin account separate. The runtime account needs the API's read access plus `SELECT, INSERT, UPDATE` on `receivers` and `aircraft`, and `SELECT, INSERT` on `aircraft_observations`.

The external Compose network must exist on this host:

```sh
docker network inspect my_rasp_network || docker network create my_rasp_network
```

## Move USB ownership to Compose on .10

The existing host-installed readsb service currently owns the tuner. Stop it before starting the Compose controller. The host GPSD daemon also currently owns `/dev/ttyACM0`; stop its socket/service before starting the GPSD container. First update `.env` with the endpoint and token above, then run:

```sh
sudo systemctl disable --now readsb
sudo systemctl disable --now gpsd.socket gpsd.service
docker ps -a --filter name=readsb --filter name=rtl_tcp
```

If the second command lists old `readsb` or `rtl_tcp` containers, remove those listed containers by name, for example:

```sh
docker rm -f readsb rtl_tcp
```

Confirm the dongle is released before Compose takes ownership:

```sh
sudo fuser -v /dev/bus/usb/*
```

If a process is listed, identify and stop it before continuing. To return to the host-installed service later, stop the Compose `radio_control` service first and then run `sudo systemctl enable --now readsb`.

## Build and start

Build the images:

```sh
docker compose build
```

Build without cache or pull the pinned base before building:

```sh
docker compose build --no-cache
docker compose build --pull
```

Start the radio controller and API:

```sh
docker compose up -d --build gpsd radio_control adsb_api
docker compose ps
docker compose logs --tail=80 gpsd radio_control adsb_api
```

The API should be ready at `192.168.1.10:8010`. Check readiness, operating mode, and GPS fix:

```sh
python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/ready', timeout=5).status)"
python3 -c "from urllib.request import urlopen; print(urlopen('http://192.168.1.10:8010/api/v1/status', timeout=5).read().decode())"
docker compose logs --tail=80 gpsd
```

## Use Station Monitor

Choose a Hyderabad VOHS station and click **Start listening · pause ADS-B**. The controller stops readsb, tunes the SDR to the selected frequency in receive-only AM mode, and streams audio privately through the API. Click **Stop listening · resume ADS-B** to stop the audio receiver and restart readsb. ADS-B updates pause during listening and resume after readsb reconnects. Changing stations while audio is active retunes the same receiver.

The presets are based on the current published [AAI eAIP VOHS communication facilities](https://aim-india.aai.aero/eaip/eaip-v2-08-2026/eAIP/IN-AD%202.1VOHS-en-GB.html). Frequencies can change; review the current AIP before use. This setup does not transmit. Keep the stream private and verify applicable local rules before sharing or rebroadcasting it.

No decoder or GPSD port is published on the host. The API binds to `.10` at `192.168.1.10:8010` for the Windows dashboard. Keep this API port limited to the trusted local network because its audio mode controls do not require user authentication. Vite proxies its API calls to this host address:

```powershell
$env:VITE_DEV_API_TARGET = 'http://192.168.1.10:8010'
npm.cmd run dev -- --host 127.0.0.1
```

## Stop, restart, and rollback

```sh
docker compose restart gpsd radio_control adsb_api
docker compose logs -f gpsd
docker compose logs -f radio_control
docker compose logs -f adsb_api
docker compose stop gpsd radio_control
```

Stopping `gpsd` and `radio_control` releases the USB devices. To return GPS to the host daemon, stop the Compose GPSD service before running `sudo systemctl enable --now gpsd.socket gpsd.service`. To roll back to host readsb, stop `radio_control` first and then run `sudo systemctl enable --now readsb`. `docker compose down` removes project containers but leaves the external network and MySQL database intact.

## Troubleshooting

### `radio_control` exits during startup

Check that `RADIO_CONTROL_TOKEN` is set in `.env`, the external network exists, the RTL-SDR is present, and no host process owns it:

```sh
docker-compose logs --tail=80 radio_control
lsusb
sudo fuser -v /dev/bus/usb/*
```

The host `readsb` service, an old `rtl_tcp` container, or another SDR application must be stopped before this container starts.

### API reports `database_unavailable`

Check the database name, credentials, network access, and table grants. MySQL error 1049 means the database name does not exist; 1045 means MySQL rejected the account or client host. Apply `backend/migrations/001_initial.sql` to the existing `adsb` schema with an authorized migration account, then check that `schema_migrations` contains version 1. Do not enable remote MySQL root access for the application.

### Audio switching fails

Check the radio controller logs and USB owner. The controller accepts only station IDs in `backend/stations.json` and only starts the audio process after stopping readsb. If the tuner cannot open or the decoder restart fails, the API returns `receiver_switch_failed`; inspect `docker-compose logs --tail=80 radio_control` before retrying.

### Legacy Compose reports `KeyError: 'ContainerConfig'`

Remove and recreate only the API service container:

```sh
docker compose rm -sf adsb_api
docker compose up -d --build --no-deps adsb_api
```

If recreating the USB-owning controller, stop it only when you intend to stop reception, then use `docker compose up -d --build radio_control`.
