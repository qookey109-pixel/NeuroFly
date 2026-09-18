from __future__ import annotations

import copy
import json
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .brain_runtime import DemoBrain, MaleCNSBrain
from .environment_adapter import EnvironmentSession, make_environment_adapter


PLATFORM_STATE_SCHEMA = "neurofly-platform-live-state-v0.1"


def _build_brain(kind: str, checkpoint: str | Path | None):
    if kind == "demo":
        return DemoBrain()
    if kind == "malecns":
        return MaleCNSBrain(checkpoint=checkpoint)
    raise ValueError(f"unknown brain backend: {kind}")


class PlatformService:
    """Environment-agnostic public/evaluation service.

    This service intentionally exposes public world state for visualization.
    It does not construct neural input; that remains EnvironmentAdapter's job.
    """

    def __init__(
        self,
        session: EnvironmentSession,
        *,
        tick_seconds: float = 0.6,
        running: bool = True,
    ) -> None:
        self.session = session
        self.tick_seconds = max(0.05, float(tick_seconds))
        self.running = bool(running)
        self.phase = "ready"
        self.runtime_error: str | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._latest_state = self.session.snapshot()
        self._thread = threading.Thread(
            target=self._loop,
            name="neurofly-platform-environment",
            daemon=True,
        )

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)
        with self._lock:
            self.session.save()

    def tick_once(self) -> dict[str, Any]:
        with self._lock:
            state = self.session.tick()
            self._latest_state = copy.deepcopy(state)
            return copy.deepcopy(state)

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            if self.running:
                try:
                    self.tick_once()
                    self.phase = "ready"
                    self.runtime_error = None
                except Exception as exc:
                    self.running = False
                    self.phase = "error"
                    self.runtime_error = f"{type(exc).__name__}: {exc}"
            delay = max(0.0, self.tick_seconds - (time.monotonic() - started))
            self._stop.wait(delay)

    def state(self) -> dict[str, Any]:
        with self._lock:
            state = copy.deepcopy(self._latest_state)
            adapter = self.session.adapter
            environment = getattr(adapter, "environment", None)
            arena = {
                "cols": getattr(environment, "cols", None),
                "rows": getattr(environment, "rows", None),
            }
            return {
                "schema": PLATFORM_STATE_SCHEMA,
                "public_evaluation_state": True,
                "neural_input_authority": False,
                "environment_model": adapter.model,
                "backend": (state.get("brain") or {}).get("backend"),
                "arena": arena,
                "runtime": {
                    "running": self.running,
                    "tick_seconds": self.tick_seconds,
                    "phase": self.phase,
                    "error": self.runtime_error,
                    "persistent": self.session.checkpoint is not None,
                },
                "state": state,
            }

    def control(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if "running" in payload:
                self.running = bool(payload["running"])
            if "tick_seconds" in payload:
                value = float(payload["tick_seconds"])
                self.tick_seconds = min(10.0, max(0.05, value))
            return self.state()


def make_platform_handler(
    service: PlatformService,
    site_dir: Path,
) -> Callable[..., SimpleHTTPRequestHandler]:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)

        def end_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Cache-Control",
                "no-store" if self.path.startswith("/api/") else "no-cache",
            )
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
            if path == "/api/platform/status":
                state = service.state()
                self._json(
                    {
                        "ok": state["runtime"]["phase"] != "error",
                        "schema": PLATFORM_STATE_SCHEMA,
                        "environment_model": state["environment_model"],
                        "backend": state["backend"],
                        "running": state["runtime"]["running"],
                        "phase": state["runtime"]["phase"],
                        "error": state["runtime"]["error"],
                    }
                )
                return
            if path == "/api/platform/state":
                self._json(service.state())
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/api/platform/control":
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


def run_platform_server(
    *,
    environment: str,
    brain: str = "demo",
    host: str = "127.0.0.1",
    port: int = 8877,
    tick_seconds: float = 0.6,
    checkpoint: str | Path | None = None,
    checkpoint_every: float = 300.0,
    seed: int = 109,
    site_dir: str | Path | None = None,
) -> None:
    backend = _build_brain(brain, checkpoint)
    adapter = make_environment_adapter(environment, seed=seed)
    session = EnvironmentSession(
        backend,
        adapter,
        checkpoint=checkpoint,
        checkpoint_every=checkpoint_every,
    )
    service = PlatformService(session, tick_seconds=tick_seconds)
    root = Path(site_dir) if site_dir else Path.cwd() / "site"
    if not root.exists():
        raise FileNotFoundError(f"Site directory not found: {root}")

    service.start()
    server = ThreadingHTTPServer(
        (host, int(port)),
        make_platform_handler(service, root),
    )
    print(
        f"NeuroFly Platform server ({adapter.model}): "
        f"http://{host}:{port}/platform.html"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        service.stop()
