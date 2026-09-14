from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import proprioception_connectivity_audit as audit


FROZEN_CONNECTIVITY_SHA256 = (
    "353e2771de973ad638878eac9fb1f76e742f928d2cc638c45f1b50775fce2e0e"
)
DISCOVERY_RUN_ID = 34809806467


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    """Verify the exact prepared receipt discovered in run 34809806467.

    The frozen digest is a reproducibility receipt only. It is not a similarity
    threshold and does not authorize promotion, stimulation, tuning identity, or
    current calibration.
    """

    previous = audit.EXPECTED_CONNECTIVITY_SHA256
    audit.EXPECTED_CONNECTIVITY_SHA256 = FROZEN_CONNECTIVITY_SHA256
    try:
        return audit.run_audit(output=output)
    finally:
        audit.EXPECTED_CONNECTIVITY_SHA256 = previous


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the frozen MaleCNS connectivity receipt for SNpp41 body 905407"
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/snpp41-body905407-connectivity-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
