from __future__ import annotations

import argparse
import json
import platform
import queue
import threading
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
    "world_ticks",
    "total_world_ticks",
    "world_tick_seconds",
    "state_kind",
    "decision_action",
    "decision_applied",
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
        if key in state:
            public[key] = state.get(key)
    return public


class LiveStatePump:
    """Publish visualization asynchronously so relay latency cannot slow science."""

    def __init__(self, publisher: GitHubOIDCLivePublisher | None, *, max_pending: int = 32) -> None:
        self.publisher = publisher
        self._queue: queue.Queue[tuple[int, dict[str, Any]]] = queue.Queue(maxsize=max_pending)
        self._stop = threading.Event()
        self._sequence = 0
        self._sequence_lock = threading.Lock()
        self._published = 0
        self._published_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        if publisher is not None:
            self._thread = threading.Thread(
                target=self._worker,
                name="neurofly-live-publisher",
                daemon=True,
            )
            self._thread.start()

    @property
    def published(self) -> int:
        with self._published_lock:
            return self._published

    def submit(self, state: dict[str, Any]) -> bool:
        if self.publisher is None or not _neural_decision_verified(state):
            return False
        public = _public_goal_state(state)
        with self._sequence_lock:
            self._sequence += 1
            sequence = self._sequence
        item = (sequence, public)
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(item)
                return True
            except queue.Full:
                return False

    def _worker(self) -> None:
        assert self.publisher is not None
        while not self._stop.is_set() or not self._queue.empty():
            try:
                sequence, state = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self.publisher.publish(state, sequence=sequence):
                    with self._published_lock:
                        self._published += 1
            finally:
                self._queue.task_done()

    def close(self, *, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)


def run_self_training(
    *,
    steps: int = 1200,
    checkpoint: str | Path = "runs/free-malecns/brain.npz",
    receipt: str | Path = "runs/free-malecns/self-training-receipt.json",
    seed: int = 109,
    allow_low_memory: bool = False,
    playback_steps: int = 240,
    world_tick_seconds: float = 0.5,
) -> dict[str, Any]:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if playback_steps < 1:
        raise ValueError("playback_steps must be >= 1")
    if world_tick_seconds <= 0:
        raise ValueError("world_tick_seconds must be > 0")

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
    session = GoalMazeSession(
        brain,
        checkpoint=checkpoint,
        seed=seed,
        world_tick_seconds=world_tick_seconds,
    )
    live = GitHubOIDCLivePublisher.from_environment()
    pump = LiveStatePump(live)
    clears_before = session.environment.total_clears
    observations: list[dict[str, Any]] = []
    playback: deque[dict[str, Any]] = deque(maxlen=playback_steps)
    world_states_seen = 0

    def on_world_tick(state: dict[str, Any]) -> None:
        nonlocal world_states_seen
        world_states_seen += 1
        pump.submit(state)

    try:
        for index in range(1, steps + 1):
            state = session.tick(on_world_tick=on_world_tick)
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
                    "action": state.get("decision_action") or state["last_action"],
                    "decision_applied": state.get("decision_applied", True),
                    "state_kind": state.get("state_kind", "neural_decision"),
                    "reward": state["last_reward"],
                    "event": state.get("step_event"),
                    "food_left": state["food_left"],
                    "total_clears": state.get("total_clears", 0),
                    "total_deaths": state.get("total_deaths", 0),
                    "world_ticks": state.get("world_ticks", 0),
                    "total_world_ticks": state.get("total_world_ticks", 0),
                    "brain_ms": telemetry.get("brain_ms"),
                    "compute_seconds": telemetry.get("compute_seconds"),
                    "total_spikes": telemetry.get("total_spikes"),
                    "memory_sha256": (telemetry.get("memory") or {}).get("sha256"),
                }
            )
            playback.append(public_state)
            pump.submit(state)
            print(
                "MALECNS_DECISION",
                index,
                "kind=", state.get("state_kind"),
                "action=", state.get("decision_action") or state["last_action"],
                "applied=", state.get("decision_applied", True),
                "world_ticks=", state.get("total_world_ticks", 0),
                flush=True,
            )
    finally:
        pump.close()

    session.save()
    final_state = _public_goal_state(session.snapshot())
    clears_after = int(final_state.get("total_clears") or 0)
    finished = time.time()
    body: dict[str, Any] = {
        "schema": "neurofly-self-training-v2",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
        "goal": "maze_cleared",
        "stonkfly_commit": STONKFLY_COMMIT,
        "seed": seed,
        "steps": steps,
        "playback_steps": len(playback),
        "world_tick_seconds": world_tick_seconds,
        "world_states_seen": world_states_seen,
        "live_published": pump.published,
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
    parser.add_argument("--world-tick-seconds", type=float, default=0.5)
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
        world_tick_seconds=args.world_tick_seconds,
        allow_low_memory=args.allow_low_memory,
    )
    summary = {
        "passed": result["passed"],
        "goal": result["goal"],
        "steps": result["steps"],
        "batch_clears": result["batch_clears"],
        "total_clears": result["clears_after"],
        "world_states_seen": result["world_states_seen"],
        "live_published": result["live_published"],
        "receipt_sha256": result["receipt_sha256"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
