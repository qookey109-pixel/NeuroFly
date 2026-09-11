from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

from .upstream import STONKFLY_COMMIT


VALID_ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_receipt(receipt: dict[str, Any]) -> None:
    supplied_digest = receipt.get("receipt_sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise ValueError("Receipt SHA-256 is missing or malformed")

    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if _digest_json(unsigned) != supplied_digest:
        raise ValueError("Receipt SHA-256 does not match receipt contents")

    if receipt.get("schema") != "neurofly-real-smoke-v2":
        raise ValueError("Unsupported real-smoke receipt schema")
    if receipt.get("passed") is not True:
        raise ValueError("Real MaleCNS smoke did not pass")
    if receipt.get("backend") != "malecns":
        raise ValueError("Receipt backend is not MaleCNS")
    if receipt.get("neural_activity_verified") is not True:
        raise ValueError("Receipt does not certify neural activity")
    if receipt.get("stonkfly_commit") != STONKFLY_COMMIT:
        raise ValueError("Receipt Stonkfly revision does not match the NeuroFly pin")

    trajectory = receipt.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        raise ValueError("Receipt does not contain a MaleCNS trajectory")

    for index, state in enumerate(trajectory, start=1):
        if not isinstance(state, dict):
            raise ValueError(f"Trajectory state {index} is not an object")
        brain = state.get("brain") or {}
        telemetry = brain.get("telemetry") or {}
        if brain.get("backend") != "malecns":
            raise ValueError(f"Trajectory state {index} is not MaleCNS")
        if state.get("last_action") not in VALID_ACTIONS:
            raise ValueError(f"Trajectory state {index} has an invalid action")
        try:
            brain_ms = float(telemetry.get("brain_ms"))
            total_spikes = int(telemetry.get("total_spikes"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Trajectory state {index} lacks neural telemetry") from exc
        if not math.isfinite(brain_ms) or brain_ms <= 0 or total_spikes <= 0:
            raise ValueError(f"Trajectory state {index} lacks verifiable neural activity")


def build_site_state(receipt: dict[str, Any]) -> dict[str, Any]:
    verify_receipt(receipt)
    return {
        "schema": "neurofly-malecns-site-state-v1",
        "verified": True,
        "backend": "malecns",
        "mode": "recorded-malecns",
        "generated_unix": time.time(),
        "source_receipt_sha256": receipt["receipt_sha256"],
        "stonkfly_commit": receipt["stonkfly_commit"],
        "steps": receipt["steps"],
        "trajectory": receipt["trajectory"],
        "final_state": receipt["final_state"],
    }


def publish_site_state(
    *,
    receipt_path: str | Path,
    output_path: str | Path = "site/malecns-state.json",
) -> dict[str, Any]:
    receipt_path = Path(receipt_path)
    output_path = Path(output_path)
    receipt = json.loads(receipt_path.read_text())
    if not isinstance(receipt, dict):
        raise ValueError("Receipt must be a JSON object")
    state = build_site_state(receipt)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".partial")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    temporary.replace(output_path)
    return state
