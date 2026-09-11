from __future__ import annotations

import hashlib
import json
import platform
import time
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .maze_runtime import MazeSession
from .preflight import collect_preflight
from .upstream import STONKFLY_COMMIT


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def run_real_smoke(
    *,
    steps: int = 1,
    checkpoint: str | Path = "runs/maze-fly-001/brain.npz",
    receipt: str | Path = "runs/maze-fly-001/real-smoke-receipt.json",
    seed: int = 109,
    allow_low_memory: bool = False,
) -> dict[str, Any]:
    if steps < 1:
        raise ValueError("steps must be >= 1")

    preflight = collect_preflight()
    if not preflight["ready"]:
        failed = [c["name"] for c in preflight["checks"] if c["required"] and not c["ok"]]
        raise RuntimeError("MaleCNS preflight failed: " + ", ".join(failed))
    if preflight["low_memory_guard"] and not allow_low_memory:
        raise RuntimeError(
            "Host memory is below the 12 GiB low-memory guard. "
            "Use a larger host or explicitly pass --allow-low-memory."
        )

    checkpoint = Path(checkpoint)
    receipt = Path(receipt)
    started = time.time()
    brain = MaleCNSBrain(checkpoint=checkpoint)
    session = MazeSession(brain, checkpoint=checkpoint, seed=seed)
    observations: list[dict[str, Any]] = []

    for index in range(1, steps + 1):
        state = session.tick()
        telemetry = state["brain"]["telemetry"]
        observations.append(
            {
                "step": index,
                "episode": state["episode"],
                "action": state["last_action"],
                "reward": state["last_reward"],
                "event": state.get("step_event"),
                "brain_ms": telemetry.get("brain_ms"),
                "compute_seconds": telemetry.get("compute_seconds"),
                "total_spikes": telemetry.get("total_spikes"),
                "reward_spikes": telemetry.get("reward_spikes"),
                "aversive_spikes": telemetry.get("aversive_spikes"),
                "kc_spikes": telemetry.get("kc_spikes"),
                "memory_sha256": (telemetry.get("memory") or {}).get("sha256"),
            }
        )

    session.save()
    finished = time.time()
    body: dict[str, Any] = {
        "schema": "neurofly-real-smoke-v1",
        "passed": True,
        "backend": "malecns",
        "stonkfly_commit": STONKFLY_COMMIT,
        "seed": seed,
        "steps": steps,
        "started_unix": started,
        "finished_unix": finished,
        "wall_seconds": round(finished - started, 6),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "preflight": preflight,
        "checkpoint": str(checkpoint),
        "observations": observations,
    }
    body["receipt_sha256"] = _digest_json(body)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    tmp = receipt.with_suffix(receipt.suffix + ".partial")
    tmp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    tmp.replace(receipt)
    return body
