from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any


AUDIENCE = "neurofly-live-relay"


def _decode_exp(token: str) -> float:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
        return float(data.get("exp", 0))
    except Exception:
        return 0.0


class GitHubOIDCLivePublisher:
    def __init__(self, relay_url: str) -> None:
        self.relay_url = relay_url.rstrip("/")
        self._token = ""
        self._token_exp = 0.0
        self._warned = False

    @classmethod
    def from_environment(cls) -> "GitHubOIDCLivePublisher | None":
        relay_url = os.environ.get("NEUROFLY_LIVE_RELAY_URL", "").strip()
        if not relay_url:
            return None
        if not os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL") or not os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
            print("LIVE_RELAY_DISABLED GitHub OIDC environment is unavailable", flush=True)
            return None
        return cls(relay_url)

    def _oidc_token(self) -> str:
        if self._token and time.time() < self._token_exp - 30:
            return self._token
        request_url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
        separator = "&" if "?" in request_url else "?"
        url = request_url + separator + urllib.parse.urlencode({"audience": AUDIENCE})
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read())
        token = str(payload["value"])
        self._token = token
        self._token_exp = _decode_exp(token)
        return token

    def publish(self, state: dict[str, Any], *, sequence: int) -> bool:
        body = json.dumps({"state": state, "sequence": sequence}, separators=(",", ":")).encode()
        try:
            token = self._oidc_token()
            req = urllib.request.Request(
                self.relay_url + "/publish",
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "NeuroFly-GitHub-Actions",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                ok = 200 <= response.status < 300
            if ok:
                self._warned = False
            return ok
        except Exception as exc:
            # Visualization transport must never corrupt or stop the scientific run.
            if not self._warned:
                print(f"LIVE_RELAY_WARNING {type(exc).__name__}: {exc}", flush=True)
                self._warned = True
            return False
