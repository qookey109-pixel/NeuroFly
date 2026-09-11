from __future__ import annotations

import json
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .brain_runtime import DemoBrain, MaleCNSBrain
from .maze_runtime import MazeSession


class MazeService:
    def __init__(self, session: MazeSession, *, tick_seconds: float = 0.6) -> None:
        self.session = session
        self.tick_seconds = max(0.05, float(tick_seconds))
        self.running = True
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._thread = threading.Thread(target=self._loop, name="neurofly-maze", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        with self._lock:
            self.session.save()

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            if self.running:
                with self._lock:
                    self.session.tick()
            delay = max(0.0, self.tick_seconds - (time.monotonic() - started))
            self._stop.wait(delay)

    def state(self) -> dict[str, Any]:
        with self._lock:
            data = self.session.snapshot()
        data["runtime"] = {
            "running": self.running,
            "tick_seconds": self.tick_seconds,
            "persistent": True,
        }
        return data

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self.session.environment.reset("manual_reset")
            return self.state()

    def control(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "running" in payload:
            self.running = bool(payload["running"])
        if "tick_seconds" in payload:
            value = float(payload["tick_seconds"])
            self.tick_seconds = min(10.0, max(0.05, value))
        if payload.get("reset"):
            return self.reset()
        return self.state()


def build_brain(kind: str, *, checkpoint: str | Path | None = None):
    if kind == "demo":
        return DemoBrain()
    if kind == "malecns":
        return MaleCNSBrain(checkpoint=checkpoint)
    raise ValueError(f"Unknown brain backend: {kind}")


def make_handler(service: MazeService, site_dir: Path) -> Callable[..., SimpleHTTPRequestHandler]:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)

        def end_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
            super().end_headers()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()

        def _json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/status":
                state = service.state()
                self._json(
                    {
                        "ok": True,
                        "backend": state["brain"]["backend"],
                        "running": state["runtime"]["running"],
                        "persistent": True,
                    }
                )
                return
            if path == "/api/state":
                self._json(service.state())
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/api/control":
                self._json({"ok": False, "error": "not_found"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError("JSON object required")
                self._json(service.control(payload))
            except (ValueError, json.JSONDecodeError) as exc:
                self._json({"ok": False, "error": str(exc)}, 400)

        def log_message(self, format: str, *args: Any) -> None:
            if self.path.startswith("/api/"):
                return
            super().log_message(format, *args)

    return Handler


def run_server(
    *,
    brain: str = "demo",
    host: str = "127.0.0.1",
    port: int = 8765,
    tick_seconds: float = 0.6,
    checkpoint: str | Path | None = None,
    site_dir: str | Path | None = None,
) -> None:
    backend = build_brain(brain, checkpoint=checkpoint)
    session = MazeSession(backend, checkpoint=checkpoint)
    service = MazeService(session, tick_seconds=tick_seconds)
    service.start()

    root = Path(site_dir) if site_dir else Path.cwd() / "site"
    if not root.exists():
        service.stop()
        raise FileNotFoundError(f"Site directory not found: {root}")

    server = ThreadingHTTPServer((host, int(port)), make_handler(service, root))
    print(f"NeuroFly Maze server: http://{host}:{port}")
    print(f"Brain backend: {brain}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        service.stop()
