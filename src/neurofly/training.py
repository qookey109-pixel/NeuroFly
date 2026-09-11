from __future__ import annotations

import argparse
import json
import platform
import time
from collections import deque
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .goal_training import GoalMazeSession
from .live_relay import GitHubOIDCLivePublisher
from .preflight import collect_preflight
from .smoke import _digest_json, _neural_decision_verified, _public_maze_state
from .upstream import STONKFLY_COMMIT


GOAL_FIELDS = (
    "goal",
    "total_ticks",
    "clear_history",
    "first_clear_seconds",
    "latest_clear_seconds",
    "best_clear_seconds",
    "first_clear_ticks",
    "latest_clear_ticks",
    "best_clear_ticks",
)


def _public_goal_state(state: dict[str, Any]) -> dict[str, Any]:
    public = _public_maze_state(state)
    for key in GOAL_FIELDS:
        public[key] = state.get(key)
    return public


def run_self_training(
    *,
    steps: int = 1200,
    checkpoint: str | Path = "runs/free-malecns/brain.npz",
    receipt: str | Path = "runs/free-malecns/self-training-receipt.json",
    seed: int = 109,
    allow_low_memory: bool = False,
    playback_steps: int = 240,
) -> dict[str, Any]:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if playback_steps < 1:
        raise ValueError("playback_steps must be >= 1")

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
    session = GoalMazeSession(brain, checkpoint=checkpoint, seed=seed)
    live = GitHubOIDCLivePublisher.from_environment()
    clears_before = session.environment.total_clears
    observations: list[dict[str, Any]] = []
    playback: deque[dict[str, Any]] = deque(maxlen=playback_steps)
    live_published = 0

    for index in range(1, steps + 1):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError(
                "MaleCNS returned a decision without verifiable neural activity; refusing to continue training"
            )
        telemetry = state["brain"]["telemetry"]
        public_state = _public_goal_state(state)
        observations.append(
            {
                "step": index,
                "episode": state["episode"],
                "action": state["last_action"],
                "reward": state["last_reward"],
                "event": state.get("step_event"),
                "food_left": state["food_left"],
                "total_clears": state.get("total_clears", 0),
                "total_deaths": state.get("total_deaths", 0),
                "brain_ms": telemetry.get("brain_ms"),
                "compute_seconds": telemetry.get("compute_seconds"),
                "total_spikes": telemetry.get("total_spikes"),
                "memory_sha256": (telemetry.get("memory") or {}).get("sha256"),
            }
        )
        playback.append(public_state)

        if live is not None and live.publish(public_state, sequence=session.environment.total_ticks):
            live_published += 1
            print(
                "LIVE_MALECNS_DECISION",
                session.environment.total_ticks,
                public_state["last_action"],
                public_state.get("last_event"),
                flush=True,
            )

    session.save()
    final_state = _public_goal_state(session.snapshot())
    clears_after = int(final_state.get("total_clears") or 0)
    finished = time.time()
    body: dict[str, Any] = {
        "schema": "neurofly-self-training-v1",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
        "goal": "maze_cleared",
        "stonkfly_commit": STONKFLY_COMMIT,
        "seed": seed,
        "steps": steps,
        "playback_steps": len(playback),
        "live_published": live_published,
        "started_unix": started,
        "finished_unix": finished,
        "wall_seconds": round(finished - started, 6),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "preflight": preflight,
        "checkpoint": str(checkpoint),
        "reward_policy": {
            "step": -0.01,
            "food": 1.0,
            "energy_food": 2.0,
            "captured": -10.0,
            "maze_cleared": 100.0,
        },
        "clears_before": clears_before,
        "clears_after": clears_after,
        "batch_clears": max(0, clears_after - clears_before),
        "observations": observations,
        "trajectory": list(playback),
        "final_state": final_state,
    }
    body["receipt_sha256"] = _digest_json(body)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_suffix(receipt.suffix + ".partial")
    temporary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    temporary.replace(receipt)
    return body


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run resumable goal-driven MaleCNS self-training")
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--checkpoint", default="runs/free-malecns/brain.npz")
    parser.add_argument("--receipt", default="runs/free-malecns/self-training-receipt.json")
    parser.add_argument("--seed", type=int, default=109)
    parser.add_argument("--playback-steps", type=int, default=240)
    parser.add_argument("--allow-low-memory", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_self_training(
        steps=args.steps,
        checkpoint=args.checkpoint,
        receipt=args.receipt,
        seed=args.seed,
        playback_steps=args.playback_steps,
        allow_low_memory=args.allow_low_memory,
    )
    summary = {
        "passed": result["passed"],
        "goal": result["goal"],
        "steps": result["steps"],
        "batch_clears": result["batch_clears"],
        "total_clears": result["clears_after"],
        "live_published": result["live_published"],
        "receipt_sha256": result["receipt_sha256"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
