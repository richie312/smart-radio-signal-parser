# Docker build and runbook

Run commands from the repository root on `.10`. Compose builds a radio controller image, a GPSD sidecar, and the API image. The radio controller runs one receive process at a time on its selected ADS-B dongle: readsb for ADS-B, or rtl_fm plus FFmpeg for airband AM audio. The optional V4 `rtl_tcp` service can run simultaneously when configured to use a different dongle. The GPSD sidecar owns the VK-172 USB serial device and shares the live site fix with the API only on the Docker network. The API proxies browser audio and reads GPSD JSON; it has no USB device mapping or Docker socket.

| Service | Purpose |
| --- | --- |
| `radio_control` | Uses the configured ADS-B RTL-SDR and switches between readsb JSON/SBS output and one selected Hyderabad airband frequency. |
| `rtl_tcp` (optional profile) | Serves raw IQ from a separately selected RTL-SDR, such as the RTL-SDR Blog V4, on TCP 1234. |
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

The API should be ready at `192.168.1.10:8010`. Readsb's BaseStation/SBS feed is also published at `192.168.1.10:30003` for a VRS receiver on the LAN. This feed is available only while the SDR is in ADS-B mode; the Station Monitor stops readsb while airband audio is active. Check readiness, operating mode, and GPS fix:

```sh
python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/ready', timeout=5).status)"
python3 -c "from urllib.request import urlopen; print(urlopen('http://192.168.1.10:8010/api/v1/status', timeout=5).read().decode())"
docker compose logs --tail=80 gpsd
```

### Connect Windows VRS

Install and run VRS on the Windows laptop. In VRS, add a receiver under **Tools → Options → Receivers** with format **BaseStation**, host/address `192.168.1.10`, and port `30003`. Configure VRS to connect to the feed (not push to it), then apply the settings. On `.10`, confirm the listener is published with `docker-compose port radio_control 30003`; from Windows, confirm reachability with `Test-NetConnection 192.168.1.10 -Port 30003`. If the host firewall is enabled, allow inbound TCP 30003 from the trusted LAN. The receiver will report disconnected while airband listening is active and reconnect when readsb resumes.

## Use Station Monitor

Choose a Hyderabad VOHS station and click **Start listening · pause ADS-B**. The controller stops readsb, tunes the SDR to the selected frequency in receive-only AM mode, and streams audio privately through the API. Click **Stop listening · resume ADS-B** to stop the audio receiver and restart readsb. ADS-B updates pause during listening and resume after readsb reconnects. Changing stations while audio is active retunes the same receiver.

The presets are based on the current published [AAI eAIP VOHS communication facilities](https://aim-india.aai.aero/eaip/eaip-v2-08-2026/eAIP/IN-AD%202.1VOHS-en-GB.html). Frequencies can change; review the current AIP before use. This setup does not transmit. Keep the stream private and verify applicable local rules before sharing or rebroadcasting it.

No decoder or GPSD port is published on the host. The API binds to `.10` at `192.168.1.10:8010` for the dashboard. Keep this API port limited to the trusted local network because its audio mode controls do not require user authentication. The React/Vite development server runs in the `frontend` container and proxies API calls to `adsb_api` over the Compose network. Start it on `.10` and open it from a LAN client:

```sh
docker compose up -d --build frontend
sudo ufw allow from 192.168.1.0/24 to any port 5173 proto tcp
```

Open `http://192.168.1.10:5173`. Follow its output with `docker compose logs -f frontend`.

Browser geolocation is restricted on an insecure HTTP LAN origin such as `http://192.168.1.10`. Set the site's fixed fallback coordinates in `.env` as `DEFAULT_SITE_LATITUDE` and `DEFAULT_SITE_LONGITUDE`; the frontend uses the GPSD fix first, browser location when available, then this static marker. Recreate the frontend after changing them:

```sh
docker compose up -d --build --force-recreate frontend
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

## Run RTL-SDR Blog V4 (`rtl_tcp`) alongside ADS-B

The ADS-B and V4 services can run together when each selects a different RTL-SDR. The Compose defaults assign device index `0` to readsb and index `1` to `rtl_tcp`. Device selection accepts an index or USB serial. If you know the unique serials, use those in `.env` for stable selection across USB re-enumeration:

```sh
READSB_DEVICE=0
RTL_TCP_DEVICE=1
RTL_TCP_GAIN=40
```

`RTL_TCP_GAIN` sets the server's initial manual tuner gain in dB (default 40). An RTL-TCP client such as SDR++ can override gain after connecting, so keep its saved tuner gain or Tuner AGC setting at a useful value too.

Start the ADS-B stack and V4 independently; do not stop `radio_control` when starting V4:

```sh
docker compose up -d radio_control adsb_api
docker compose --profile rtl_tcp up -d --build rtl_tcp
docker compose logs -f rtl_tcp
```

The `rtl_tcp` service publishes raw IQ on `192.168.1.10:1234`. If UFW is enabled, allow it from the trusted LAN:

```sh
sudo ufw allow from 192.168.1.0/24 to any port 1234 proto tcp
```

Stop only V4 when you no longer need its raw-IQ stream; ADS-B keeps running:

```sh
docker compose --profile rtl_tcp stop rtl_tcp
```

The earlier V4 log showed it accepting clients before `Signal caught, exiting!` and `bye!`; those messages indicate process shutdown, not a tuner failure. If it exits again, check the container's exit details and confirm `RTL_TCP_DEVICE` and `READSB_DEVICE` select different dongles.

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
