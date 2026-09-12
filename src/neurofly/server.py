from __future__ import annotations

import json
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .brain_runtime import DemoBrain, MaleCNSBrain, brain_status
from .maze_runtime import MazeSession
from .preflight import collect_preflight


class MazeService:
    def __init__(
        self,
        session: MazeSession,
        *,
        tick_seconds: float = 0.6,
        running: bool = True,
        phase: str = "ready",
    ) -> None:
        self.session = session
        self.tick_seconds = max(0.05, float(tick_seconds))
        self.running = bool(running)
        self.phase = phase
        self.runtime_error: str | None = None
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

    def set_phase(self, phase: str, *, error: str | None = None) -> None:
        with self._lock:
            self.phase = phase
            self.runtime_error = error

    def replace_session(self, session: MazeSession, *, phase: str) -> None:
        with self._lock:
            self.session = session
            self.phase = phase
            self.runtime_error = None

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
            runtime = {
                "running": self.running,
                "tick_seconds": self.tick_seconds,
                "persistent": True,
                "phase": self.phase,
                "error": self.runtime_error,
            }
        data["runtime"] = runtime
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
                        "ok": state["runtime"]["phase"] != "error",
                        "backend": state["brain"]["backend"],
                        "running": state["runtime"]["running"],
                        "persistent": True,
                        "phase": state["runtime"]["phase"],
                        "error": state["runtime"]["error"],
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


def _serve(service: MazeService, *, host: str, port: int, site_dir: str | Path | None) -> None:
    root = Path(site_dir) if site_dir else Path.cwd() / "site"
    if not root.exists():
        service.stop()
        raise FileNotFoundError(f"Site directory not found: {root}")

    server = ThreadingHTTPServer((host, int(port)), make_handler(service, root))
    print(f"NeuroFly Maze server: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        service.stop()


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
    print(f"Brain backend: {brain}")
    _serve(service, host=host, port=port, site_dir=site_dir)


def run_cloud_server(
    *,
    host: str = "0.0.0.0",
    port: int = 8765,
    tick_seconds: float = 0.6,
    checkpoint: str | Path = "/var/data/neurofly/maze-fly-001/brain.npz",
    site_dir: str | Path | None = None,
) -> None:
    """Start HTTP immediately, prepare MaleCNS on the runtime disk, then promote.

    The bootstrap session is paused and has no checkpoint, so no DemoBrain
    actions are mixed into the persistent experiment while MaleCNS data is
    being downloaded/verified/compiled.
    """

    bootstrap = MazeSession(DemoBrain(), checkpoint=None)
    service = MazeService(
        bootstrap,
        tick_seconds=tick_seconds,
        running=False,
        phase="preparing-malecns",
    )
    service.start()

    def prepare_and_promote() -> None:
        try:
            status = brain_status()
            if not status.get("prepared"):
                from stonkfly.data import prepare

                prepare()
            report = collect_preflight()
            if not report["ready"]:
                failed = [
                    item["name"]
                    for item in report["checks"]
                    if item["required"] and not item["ok"]
                ]
                raise RuntimeError("MaleCNS preflight failed after prepare: " + ", ".join(failed))
            backend = MaleCNSBrain(checkpoint=checkpoint)
            session = MazeSession(backend, checkpoint=checkpoint)
            service.replace_session(session, phase="malecns-ready")
            service.running = True
            print("MaleCNS prepared and promoted to Maze authority", flush=True)
        except Exception as exc:
            service.running = False
            service.set_phase("error", error=f"{type(exc).__name__}: {exc}")
            print(f"MaleCNS cloud bootstrap failed: {type(exc).__name__}: {exc}", flush=True)

    threading.Thread(
        target=prepare_and_promote,
        name="neurofly-malecns-prepare",
        daemon=True,
    ).start()
    print("Brain backend: cloud bootstrap (paused until MaleCNS is ready)")
    _serve(service, host=host, port=port, site_dir=site_dir)
