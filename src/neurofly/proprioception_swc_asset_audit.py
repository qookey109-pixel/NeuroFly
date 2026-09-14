from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-snpp41-swc-asset-audit-v1"
STATUS_DISCOVERY = "DISCOVERY_REQUIRED"
STATUS_REVIEW = "REVIEW_REQUIRED"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
VFB_ID = "VFB_jrmc173b"
SWC_URL = "https://www.virtualflybrain.org/data/VFB/i/jrmc/173b/VFB_00200000/volume.swc"
EXPECTED_SWC_SHA256: str | None = (
    "a85f11d845f885c15ca9f79743e79a1a19e3a85000f0997e5ccc0e4be8f08211"
)
EXPECTED_STATS_SHA256: str | None = (
    "07350bda394d0e8a61b6b1285abb825af0a6f607620d7431f4a8ea4205ac4eea"
)


def _download_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NeuroFly/0.4 swc-asset-audit"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    if not payload:
        raise ValueError("Downloaded SWC is empty")
    return payload


def _parse_swc(payload: bytes) -> dict[int, tuple[int, float, float, float, float, int]]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("SWC must be UTF-8 text") from exc

    nodes: dict[int, tuple[int, float, float, float, float, int]] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 7:
            raise ValueError(f"Malformed SWC line {line_number}: expected 7 columns")
        try:
            node_id = int(fields[0])
            node_type = int(fields[1])
            x = float(fields[2])
            y = float(fields[3])
            z = float(fields[4])
            radius = float(fields[5])
            parent_id = int(fields[6])
        except ValueError as exc:
            raise ValueError(f"Malformed numeric SWC line {line_number}") from exc
        if node_id in nodes:
            raise ValueError(f"Duplicate SWC node id: {node_id}")
        if not all(math.isfinite(value) for value in (x, y, z, radius)):
            raise ValueError(f"Non-finite SWC geometry at line {line_number}")
        if radius < 0:
            raise ValueError(f"Negative SWC radius at line {line_number}")
        nodes[node_id] = (node_type, x, y, z, radius, parent_id)

    if not nodes:
        raise ValueError("SWC contains no nodes")
    for node_id, (_, _, _, _, _, parent_id) in nodes.items():
        if parent_id != -1 and parent_id not in nodes:
            raise ValueError(f"SWC node {node_id} references missing parent {parent_id}")
    return nodes


def _stats(nodes: dict[int, tuple[int, float, float, float, float, int]]) -> dict[str, Any]:
    child_counts: Counter[int] = Counter()
    root_count = 0
    cable_length = 0.0
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    type_counts: Counter[int] = Counter()

    for node_id, (node_type, x, y, z, _radius, parent_id) in nodes.items():
        xs.append(x)
        ys.append(y)
        zs.append(z)
        type_counts[node_type] += 1
        if parent_id == -1:
            root_count += 1
            continue
        child_counts[parent_id] += 1
        _, px, py, pz, _, _ = nodes[parent_id]
        cable_length += math.dist((x, y, z), (px, py, pz))

    terminal_nodes = sum(1 for node_id in nodes if child_counts[node_id] == 0)
    branch_points = sum(1 for node_id in nodes if child_counts[node_id] > 1)
    stats = {
        "node_count": len(nodes),
        "root_count": root_count,
        "terminal_nodes": terminal_nodes,
        "branch_points": branch_points,
        "cable_length": round(cable_length, 6),
        "bbox": {
            "x_min": round(min(xs), 6),
            "x_max": round(max(xs), 6),
            "y_min": round(min(ys), 6),
            "y_max": round(max(ys), 6),
            "z_min": round(min(zs), 6),
            "z_max": round(max(zs), 6),
        },
        "node_type_counts": {str(key): value for key, value in sorted(type_counts.items())},
    }
    return stats


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_report(
    payload: bytes,
    *,
    expected_swc_sha256: str | None = EXPECTED_SWC_SHA256,
    expected_stats_sha256: str | None = EXPECTED_STATS_SHA256,
) -> dict[str, Any]:
    nodes = _parse_swc(payload)
    stats = _stats(nodes)
    swc_sha = _sha256_bytes(payload)
    stats_sha = _sha256_json(stats)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": STATUS_DISCOVERY,
        "target_body_id": TARGET_BODY_ID,
        "target_type": TARGET_TYPE,
        "vfb_id": VFB_ID,
        "swc_url": SWC_URL,
        "swc_sha256": swc_sha,
        "stats": stats,
        "stats_sha256": stats_sha,
        "expected_swc_sha256": expected_swc_sha256,
        "expected_stats_sha256": expected_stats_sha256,
        "morphology_asset_verified": False,
        "peer_morphology_compared": False,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
    }
    gates = {
        "swc_nonempty": len(payload) > 0,
        "skeleton_nonempty": stats["node_count"] > 0,
        "has_root": stats["root_count"] >= 1,
        "swc_sha_frozen": expected_swc_sha256 is not None,
        "swc_sha_matches": swc_sha == expected_swc_sha256,
        "stats_sha_frozen": expected_stats_sha256 is not None,
        "stats_sha_matches": stats_sha == expected_stats_sha256,
        "current_calibration_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "promotion_remains_blocked": True,
    }
    report["gates"] = gates
    passed = all(gates.values())
    report["passed"] = passed
    if passed:
        report["status"] = STATUS_REVIEW
        report["morphology_asset_verified"] = True
    return report


def discover() -> dict[str, Any]:
    return build_report(_download_bytes(SWC_URL))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = discover()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
