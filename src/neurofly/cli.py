from __future__ import annotations

import argparse

from .experiments import list_experiments
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neurofly",
        description="Connectome-driven agent playground",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ideas", help="list the initial experiment playground")
    subparsers.add_parser("upstream-status", help="show the pinned Stonkfly integration status")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ideas":
        return _ideas()
    if args.command == "upstream-status":
        return _upstream_status()
    raise RuntimeError(f"Unhandled command: {args.command}")
