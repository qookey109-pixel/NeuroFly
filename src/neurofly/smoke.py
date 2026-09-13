from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .maze_runtime import MazeSession
from .preflight import collect_preflight
from .upstream import STONKFLY_COMMIT


VALID_ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _public_maze_state(state: dict[str, Any]) -> dict[str, Any]:
    brain = state.get("brain") or {}
    telemetry = brain.get("telemetry") or {}
    return {
        "grid": list(state.get("grid") or []),
        "fly": dict(state.get("fly") or {}),
        "enemies": [dict(enemy) for enemy in state.get("enemies") or []],
        "power_ticks": int(state.get("power_ticks") or 0),
        "episode": int(state.get("episode") or 1),
        "ticks": int(state.get("ticks") or 0),
        "episode_reward": float(state.get("episode_reward") or 0.0),
        "cumulative_reward": float(state.get("cumulative_reward") or 0.0),
        "episode_food": int(state.get("episode_food") or 0),
        "food_left": int(state.get("food_left") or 0),
        "total_deaths": int(state.get("total_deaths") or 0),
        "total_clears": int(state.get("total_clears") or 0),
        "survival_seconds": float(state.get("survival_seconds") or 0.0),
        "last_action": str(state.get("last_action") or "HOLD"),
        "last_reward": float(state.get("last_reward") or 0.0),
        "last_event": state.get("step_event") or state.get("last_event"),
        "brain": {
            "backend": str(brain.get("backend") or "unknown"),
            "telemetry": {
                "brain_ms": telemetry.get("brain_ms"),
                "compute_seconds": telemetry.get("compute_seconds"),
                "total_spikes": telemetry.get("total_spikes"),
                "reward_spikes": telemetry.get("reward_spikes"),
                "aversive_spikes": telemetry.get("aversive_spikes"),
                "kc_spikes": telemetry.get("kc_spikes"),
                "vision_model": telemetry.get("vision_model"),
                "vision": telemetry.get("vision"),
                "visual_change": telemetry.get("visual_change"),
                "visual_left_change": telemetry.get("visual_left_change"),
                "visual_right_change": telemetry.get("visual_right_change"),
                "vision_report": telemetry.get("vision_report"),
                "memory": telemetry.get("memory"),
            },
        },
    }


def _neural_decision_verified(state: dict[str, Any]) -> bool:
    brain = state.get("brain") or {}
    telemetry = brain.get("telemetry") or {}
    action = state.get("last_action")
    brain_ms = telemetry.get("brain_ms")
    total_spikes = telemetry.get("total_spikes")
    try:
        brain_ms_ok = math.isfinite(float(brain_ms)) and float(brain_ms) > 0
        spikes_ok = int(total_spikes) > 0
    except (TypeError, ValueError, OverflowError):
        return False
    return brain.get("backend") == "malecns" and action in VALID_ACTIONS and brain_ms_ok and spikes_ok


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
    public_states: list[dict[str, Any]] = []

    for index in range(1, steps + 1):
        state = session.tick()
        telemetry = state["brain"]["telemetry"]
        verified = _neural_decision_verified(state)
        if not verified:
            raise RuntimeError(
                "MaleCNS returned a decision without verifiable neural activity; refusing to publish gameplay"
            )
        public_state = _public_maze_state(state)
        public_states.append(public_state)
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
                "vision_model": telemetry.get("vision_model"),
                "visual_change": telemetry.get("visual_change"),
                "memory_sha256": (telemetry.get("memory") or {}).get("sha256"),
                "neural_activity_verified": True,
            }
        )

    session.save()
    finished = time.time()
    body: dict[str, Any] = {
        "schema": "neurofly-real-smoke-v2",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
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
        "trajectory": public_states,
        "final_state": public_states[-1],
    }
    body["receipt_sha256"] = _digest_json(body)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    tmp = receipt.with_suffix(receipt.suffix + ".partial")
    tmp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    tmp.replace(receipt)
    return body
