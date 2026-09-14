from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import proprioception_morphology_audit as audit


# Canonical receipt discovered on prepared MaleCNS / official MaleCNS v1.0 SWCs
# in workflow run 34813875795. This freezes reproducibility only; it is not a
# morphology classification threshold and does not authorize neural current.
FROZEN_MORPHOLOGY_SHA256 = (
    "a0cfd6206b92bb9179eede4c84bfd15da2b284516dfaebeb5e1b6e3c4d37b597"
)
DISCOVERY_RUN_ID = 34813875795
TARGET_RAW_SWC_SHA256 = (
    "5934c17b42edc0ea10dc75e571ca258a0321d2b72ecce796f0ee736a606aa174"
)


def run_frozen_verification(*, output: str | Path | None = None) -> dict:
    previous = audit.EXPECTED_MORPHOLOGY_SHA256
    try:
        audit.EXPECTED_MORPHOLOGY_SHA256 = FROZEN_MORPHOLOGY_SHA256
        result = audit.run_audit(output=output)
    finally:
        audit.EXPECTED_MORPHOLOGY_SHA256 = previous

    if result.get("morphology_sha256") != FROZEN_MORPHOLOGY_SHA256:
        raise RuntimeError("Official SWC morphology receipt drifted from frozen evidence")
    target = result.get("target") or {}
    morphology = target.get("morphology") or {}
    if morphology.get("swc_sha256") != TARGET_RAW_SWC_SHA256:
        raise RuntimeError("Body 905407 raw official SWC digest drifted")
    if result.get("status") != "REVIEW_REQUIRED" or result.get("passed") is not True:
        raise RuntimeError("Frozen morphology receipt did not verify as REVIEW_REQUIRED")
    if result.get("promotion_ready") is not False:
        raise RuntimeError("Morphology verification must not authorize promotion")
    if result.get("stimulation_enabled") is not False:
        raise RuntimeError("Morphology verification must not enable stimulation")
    if result.get("runtime_transduction_enabled") is not False:
        raise RuntimeError("Morphology verification must not enable runtime transduction")
    if result.get("current_calibration_authorized") is not False:
        raise RuntimeError("Morphology verification must not authorize current calibration")
    if result.get("direction_tuning_resolved") is not False:
        raise RuntimeError("Morphology verification must not invent direction tuning")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the frozen official-SWC morphology receipt for SNpp41 body 905407"
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/snpp41-body905407-morphology-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_frozen_verification(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
