"""Small, authenticated single-SDR mode controller for readsb and receive-only AM audio."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import atexit
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


PORT = int(os.getenv("RADIO_CONTROL_PORT", "8090"))
TOKEN = os.environ["RADIO_CONTROL_TOKEN"]
INITIAL_MODE = os.getenv("OPERATING_MODE", "adsb")
STATIONS = json.loads(Path("/app/stations.json").read_text())["stations"]
STATION_BY_ID = {item["station_id"]: item for item in STATIONS}
lock = threading.RLock()
stream_lock = threading.Lock()
mode = "idle"
active_station_id: str | None = None
readsb: subprocess.Popen | None = None
rtl_fm: subprocess.Popen | None = None
ffmpeg: subprocess.Popen | None = None


def stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


def stop_children() -> None:
    global readsb, rtl_fm, ffmpeg, mode, active_station_id
    stop_process(ffmpeg)
    stop_process(rtl_fm)
    stop_process(readsb)
    ffmpeg = rtl_fm = readsb = None
    mode, active_station_id = "idle", None


def shutdown(_signum=None, _frame=None):
    stop_children()
    raise SystemExit(0)


atexit.register(stop_children)
signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


def start_adsb() -> None:
    global readsb, mode, active_station_id
    stop_children()
    readsb = subprocess.Popen([
        "/usr/local/bin/readsb", "--quiet", "--net", "--device", "0",
        "--device-type", "rtlsdr", "--gain", "auto",
        "--net-bind-address", "0.0.0.0", "--net-json-port", "30006",
    ], stdout=subprocess.DEVNULL, stderr=None)
    time.sleep(0.25)
    if readsb.poll() is not None:
        code = readsb.returncode
        readsb = None
        raise RuntimeError(f"readsb exited during startup ({code})")
    mode, active_station_id = "adsb", None


def start_audio(station_id: str) -> None:
    global rtl_fm, ffmpeg, mode, active_station_id
    station = STATION_BY_ID.get(station_id)
    if station is None:
        raise ValueError("unknown_station")
    stop_children()
    frequency_hz = int(round(float(station["frequency_mhz"]) * 1_000_000))
    try:
        rtl_fm = subprocess.Popen([
            "rtl_fm", "-f", str(frequency_hz), "-M", "am", "-s", "24000",
            "-g", "40", "-l", "0", "-",
        ], stdout=subprocess.PIPE, stderr=None)
        ffmpeg = subprocess.Popen([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "s16le",
            "-ar", "24000", "-ac", "1", "-i", "pipe:0", "-b:a", "48k",
            "-f", "mp3", "pipe:1",
        ], stdin=rtl_fm.stdout, stdout=subprocess.PIPE, stderr=None)
        if rtl_fm.stdout:
            rtl_fm.stdout.close()
    except Exception:
        stop_children()
        raise
    time.sleep(0.35)
    if rtl_fm.poll() is not None or ffmpeg.poll() is not None:
        code = rtl_fm.returncode if rtl_fm.poll() is not None else ffmpeg.returncode
        stop_children()
        raise RuntimeError(f"airband audio pipeline exited during startup ({code})")
    mode, active_station_id = "aviation_audio", station_id


class Handler(BaseHTTPRequestHandler):
    server_version = "RadioControl/1.0"

    def log_message(self, fmt, *args):
        print("radio-control:", fmt % args, flush=True)

    def authorized(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def json_response(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health/live":
            return self.json_response(200, {"state": "online"})
        if not self.authorized():
            return self.json_response(401, {"error": "unauthorized"})
        if self.path == "/status":
            with lock:
                return self.json_response(200, {"mode": mode, "station_id": active_station_id})
        if self.path == "/audio/live":
            with lock:
                proc = ffmpeg if mode == "aviation_audio" else None
            if proc is None or proc.poll() is not None:
                return self.json_response(409, {"error": "audio_not_active"})
            if not stream_lock.acquire(blocking=False):
                return self.json_response(409, {"error": "audio_stream_in_use"})
            try:
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                while proc.poll() is None:
                    chunk = proc.stdout.read(4096) if proc.stdout else b""
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                stream_lock.release()
            return
        return self.json_response(404, {"error": "not_found"})

    def do_POST(self):
        if not self.authorized():
            return self.json_response(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            with lock:
                if self.path == "/mode/audio":
                    start_audio(str(body.get("station_id", "")))
                elif self.path == "/mode/adsb":
                    start_adsb()
                else:
                    return self.json_response(404, {"error": "not_found"})
                return self.json_response(200, {"mode": mode, "station_id": active_station_id})
        except ValueError as exc:
            return self.json_response(400, {"error": str(exc)})
        except Exception as exc:
            print(f"radio-control: mode switch failed ({type(exc).__name__})", flush=True)
            return self.json_response(503, {"error": "receiver_switch_failed"})


if INITIAL_MODE == "adsb":
    with lock:
        start_adsb()

server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()
