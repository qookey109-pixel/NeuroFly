from __future__ import annotations

import importlib.util
import sys
import types
from http import HTTPStatus
from pathlib import Path


def _load_relay_module():
    fake_jwt = types.ModuleType("jwt")
    fake_jwt.PyJWKClient = object
    fake_jwt.decode = lambda *args, **kwargs: {}

    previous = sys.modules.get("jwt")
    sys.modules["jwt"] = fake_jwt
    try:
        path = Path(__file__).parents[1] / "relay" / "app.py"
        spec = importlib.util.spec_from_file_location("neurofly_test_relay_app", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("jwt", None)
        else:
            sys.modules["jwt"] = previous


def _call_latest(module, monkeypatch):
    captured = {}

    def capture(_handler, status, payload):
        captured["status"] = status
        captured["payload"] = payload

    monkeypatch.setattr(module, "_json_response", capture)
    handler = module.Handler.__new__(module.Handler)
    handler.path = "/latest"
    handler.do_GET()
    return captured


def test_latest_returns_503_before_any_verified_state(monkeypatch) -> None:
    module = _load_relay_module()
    module._latest = None

    response = _call_latest(module, monkeypatch)

    assert response["status"] == HTTPStatus.SERVICE_UNAVAILABLE
    assert response["payload"] == {
        "ok": False,
        "has_state": False,
        "error": "no verified MaleCNS state published yet",
    }


def test_latest_returns_exact_verified_event(monkeypatch) -> None:
    module = _load_relay_module()
    event = {
        "schema": "neurofly-live-state-v1",
        "backend": "malecns",
        "verified": True,
        "sequence": 42,
        "relay_sequence": 123456789,
        "run_id": "999",
        "state": {
            "food_left": 7,
            "total_clears": 1,
            "total_deaths": 2,
            "fly": {"x": 4, "y": 5, "dir": "RIGHT"},
        },
    }
    module._latest = event

    response = _call_latest(module, monkeypatch)

    assert response["status"] == HTTPStatus.OK
    assert response["payload"] is event
