from __future__ import annotations

"""Audit an already-published real MaleCNS trajectory; never touch runtime."""

import argparse
import hashlib
import json
from pathlib import Path

from neurofly.odor_behavior_audit import audit_published_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="site/malecns-state.json")
    parser.add_argument("--output", default="runs/stage2-odor-action-audit/audit.json")
    args = parser.parse_args()

    path = Path(args.source)
    source = path.read_bytes()
    state = json.loads(source)
    report = audit_published_state(state)
    report["published_source_sha256"] = hashlib.sha256(source).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        "STAGE2_ODOR_ACTION_AUDIT_PASS",
        report["published_source_sha256"],
        json.dumps(report["counts"], sort_keys=True),
        "promotion_authorized=false",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
