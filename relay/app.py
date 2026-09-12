from __future__ import annotations

import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import jwt

ISSUER = "https://token.actions.githubusercontent.com"
AUDIENCE = "neurofly-live-relay"
JWKS_URL = f"{ISSUER}/.well-known/jwks"
EXPECTED_REPOSITORY = os.environ.get("NEUROFLY_EXPECTED_REPOSITORY", "qookey109-pixel/NeuroFly")
EXPECTED_REF = os.environ.get(
    "NEUROFLY_EXPECTED_REF",
    "refs/heads/main",
)
EXPECTED_WORKFLOW_PATH = ".github/workflows/full-malecns-free.yml"
VALID_ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}
MAX_PUBLISH_BODY = 1_500_000

_state_lock = threading.Condition()
_latest: dict[str, Any] | None = None
_sequence = 0


def _cors(handler: BaseHTTPRequestHandler) -> None:
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    _cors(handler)
    handler.end_headers()
    handler.wfile.write(body)


def _verify_oidc(token: str) -> dict[str, Any]:
    jwks = jwt.PyJWKClient(JWKS_URL)
    key = jwks.get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "iss", "aud", "repository", "ref"]},
    )
    if claims.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("unexpected repository")
    if claims.get("ref") != EXPECTED_REF:
        raise ValueError("unexpected ref")
    workflow_ref = str(claims.get("workflow_ref") or "")
    if EXPECTED_WORKFLOW_PATH not in workflow_ref:
        raise ValueError("unexpected workflow")
    return claims


def _verified_state(state: dict[str, Any]) -> bool:
    brain = state.get("brain") or {}
    telemetry = brain.get("telemetry") or {}
    try:
        brain_ms = float(telemetry.get("brain_ms"))
        total_spikes = int(telemetry.get("total_spikes"))
    except (TypeError, ValueError, OverflowError):
        return False
    return (
        brain.get("backend") == "malecns"
        and state.get("last_action") in VALID_ACTIONS
        and brain_ms > 0
        and total_spikes > 0
        and isinstance(state.get("grid"), list)
        and isinstance(state.get("fly"), dict)
        and isinstance(state.get("enemies"), list)
    )


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"relay {self.address_string()} {fmt % args}", flush=True)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        _cors(self)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            with _state_lock:
                seq = _sequence
                has_state = _latest is not None
            _json_response(
                self,
                HTTPStatus.OK,
                {"ok": True, "sequence": seq, "has_state": has_state, "expected_ref": EXPECTED_REF},
            )
            return

        if self.path != "/events":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        _cors(self)
        self.end_headers()

        last_seen = -1
        try:
            while True:
                with _state_lock:
                    if _sequence == last_seen:
                        _state_lock.wait(timeout=12.0)
                    seq = _sequence
                    latest = _latest
                if latest is not None and seq != last_seen:
                    payload = json.dumps(latest, separators=(",", ":"))
                    self.wfile.write(f"id: {seq}\nevent: malecns\ndata: {payload}\n\n".encode())
                    self.wfile.flush()
                    last_seen = seq
                else:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return

    def do_POST(self) -> None:
        if self.path != "/publish":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        # Always consume a bounded request body before returning an auth error.
        # Otherwise HTTP/1.1 may interpret the unread JSON bytes as the next
        # request line, producing misleading 400 "Bad request syntax" errors.
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            size = 0
        if size <= 0 or size > MAX_PUBLISH_BODY:
            self.close_connection = True
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid body size"})
            return
        body = self.rfile.read(size)

        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "missing bearer token"})
            return
        try:
            claims = _verify_oidc(auth[7:])
        except Exception as exc:
            _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": f"invalid GitHub OIDC token: {exc}"})
            return

        try:
            payload = json.loads(body)
            state = payload.get("state")
            if not isinstance(state, dict) or not _verified_state(state):
                raise ValueError("state is not verified MaleCNS telemetry")
            sequence = int(payload.get("sequence", 0))
        except Exception as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        event = {
            "schema": "neurofly-live-state-v1",
            "backend": "malecns",
            "verified": True,
            "sequence": sequence,
            "published_unix": time.time(),
            "run_id": claims.get("run_id"),
            "run_attempt": claims.get("run_attempt"),
            "state": state,
        }
        global _latest, _sequence
        with _state_lock:
            # Use wall-clock milliseconds as the floor so a fresh Render
            # instance never restarts relay_sequence at 1. This keeps already
            # open browsers accepting live events across relay redeploys.
            _sequence = max(_sequence + 1, int(time.time() * 1000))
            event["relay_sequence"] = _sequence
            _latest = event
            _state_lock.notify_all()

        # Compact live diagnostics: enough to distinguish transport problems
        # from a fly that is genuinely turning/holding in place. Avoid logging
        # the large neural payload or any credentials. Keep raw MaleCNS action
        # separate from the environment action when anti-stall intervenes.
        if sequence % 10 == 0:
            fly = state.get("fly") or {}
            print(
                "LIVE_STATE"
                f" run={claims.get('run_id')}"
                f" source_seq={sequence}"
                f" relay_seq={event['relay_sequence']}"
                f" kind={state.get('state_kind')}"
                f" action={state.get('last_action')}"
                f" raw={state.get('raw_brain_action')}"
                f" applied={state.get('applied_action')}"
                f" overridden={state.get('action_overridden')}"
                f" reason={state.get('override_reason')}"
                f" stationary={state.get('anti_stall_stationary_steps')}"
                f" pos={fly.get('x')},{fly.get('y')}"
                f" dir={fly.get('dir')}"
                f" episode={state.get('episode')}"
                f" ticks={state.get('ticks')}"
                f" world_ticks={state.get('total_world_ticks')}"
                f" total_active={state.get('total_active_seconds')}",
                flush=True,
            )

        _json_response(self, HTTPStatus.ACCEPTED, {"ok": True, "relay_sequence": _sequence})


def main() -> None:
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(
        f"NeuroFly live relay listening on :{port} for {EXPECTED_REPOSITORY} {EXPECTED_REF}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
