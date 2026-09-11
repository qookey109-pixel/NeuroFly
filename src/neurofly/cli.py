from __future__ import annotations

import argparse
import json
import time

from .brain_runtime import DemoBrain, MaleCNSBrain, brain_status
from .experiments import list_experiments
from .maze_runtime import MazeSession
from .server import run_server
from .upstream import stonkfly_status


def _ideas() -> int:
    print("NeuroFly experiment playground")
    print("==============================")
    for experiment in list_experiments():
        marker = " [external side effects]" if experiment.side_effects else ""
        print(f"- {experiment.name} ({experiment.slug}){marker}")
        print(f"  {experiment.summary}")
    return 0


def _upstream_status() -> int:
    status = stonkfly_status()
    print(f"name: {status.name}")
    print(f"installed: {'yes' if status.installed else 'no'}")
    print(f"version: {status.version or '-'}")
    print(f"repository: {status.repository}")
    print(f"pinned_commit: {status.pinned_commit}")
    if not status.installed:
        print("install: pip install -e '.[stonkfly]'")
    return 0


def _brain_status() -> int:
    print(json.dumps(brain_status(), indent=2, sort_keys=True))
    return 0


def _build_brain(kind: str, checkpoint: str | None):
    if kind == "demo":
        return DemoBrain()
    if kind == "malecns":
        return MaleCNSBrain(checkpoint=checkpoint)
    raise ValueError(f"Unknown brain backend: {kind}")


def _maze_run(args: argparse.Namespace) -> int:
    brain = _build_brain(args.brain, args.checkpoint)
    session = MazeSession(
        brain,
        checkpoint=args.checkpoint,
        checkpoint_every=args.checkpoint_every,
        seed=args.seed,
    )
    steps = 0
    try:
        while args.steps <= 0 or steps < args.steps:
            state = session.tick()
            steps += 1
            summary = {
                "step": steps,
                "episode": state["episode"],
                "action": state["last_action"],
                "reward": state["last_reward"],
                "food": state["episode_food"],
                "event": state.get("step_event"),
                "brain": state["brain"]["backend"],
            }
            print(json.dumps(summary, separators=(",", ":")), flush=True)
            if args.interval > 0:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        session.save()
    return 0


def _maze_server(args: argparse.Namespace) -> int:
    run_server(
        brain=args.brain,
        host=args.host,
        port=args.port,
        tick_seconds=args.tick_seconds,
        checkpoint=args.checkpoint,
        site_dir=args.site_dir,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neurofly",
        description="Connectome-driven agent playground",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ideas", help="list the initial experiment playground")
    subparsers.add_parser("upstream-status", help="show the pinned Stonkfly integration status")
    subparsers.add_parser("brain-status", help="verify the optional MaleCNS runtime and prepared graph")

    run = subparsers.add_parser("maze-run", help="run the persistent Maze Chase loop without a browser")
    run.add_argument("--brain", choices=("demo", "malecns"), default="demo")
    run.add_argument("--steps", type=int, default=0, help="0 means run until interrupted")
    run.add_argument("--interval", type=float, default=0.6, help="wall seconds between decisions")
    run.add_argument("--checkpoint", default="runs/maze-fly-001/brain.npz")
    run.add_argument("--checkpoint-every", type=float, default=300.0)
    run.add_argument("--seed", type=int, default=109)

    server = subparsers.add_parser("maze-server", help="serve the visualizer plus persistent Maze API")
    server.add_argument("--brain", choices=("demo", "malecns"), default="demo")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    server.add_argument("--tick-seconds", type=float, default=0.6)
    server.add_argument("--checkpoint", default="runs/maze-fly-001/brain.npz")
    server.add_argument("--site-dir", default="site")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ideas":
        return _ideas()
    if args.command == "upstream-status":
        return _upstream_status()
    if args.command == "brain-status":
        return _brain_status()
    if args.command == "maze-run":
        return _maze_run(args)
    if args.command == "maze-server":
        return _maze_server(args)
    raise RuntimeError(f"Unhandled command: {args.command}")
