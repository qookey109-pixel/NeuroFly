from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from neurofly.proprioception_peer_swc_asset_audit import (
    EXPECTED_COHORT_RECEIPT_SHA256,
    PEER_ASSETS,
)
from neurofly.proprioception_swc_asset_audit import _download_bytes, _parse_swc, _stats


SCHEMA = "neurofly-proprioception-snpp41-peer-morphology-protocol-v1"
STATUS_DISCOVERY = "DISCOVERY_REQUIRED"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_FAIL = "FAIL"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
EXPECTED_PROTOCOL_RECEIPT_SHA256: str | None = (
    "9710b3456c599af24d896a6e9b9f0b577c73cdc0eae6a3ac9260c1baf5ed8c48"
)
FEATURE_NAMES = (
    "log1p_node_count",
    "log1p_branch_points",
    "log1p_terminal_nodes",
    "log1p_cable_length",
    "branch_fraction",
    "terminal_fraction",
    "log1p_mean_edge_length",
    "log1p_bbox_extent_small",
    "log1p_bbox_extent_mid",
    "log1p_bbox_extent_large",
)
ROBUST_SCALE_FLOOR = 1e-9
MAD_NORMAL_CONSISTENCY = 1.4826
IQR_NORMAL_CONSISTENCY = 1.349


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _descriptor(stats: dict[str, Any]) -> dict[str, float]:
    node_count = float(stats["node_count"])
    branch_points = float(stats["branch_points"])
    terminal_nodes = float(stats["terminal_nodes"])
    root_count = float(stats["root_count"])
    cable_length = float(stats["cable_length"])
    edge_count = max(node_count - root_count, 1.0)
    bbox = stats["bbox"]
    extents = sorted(
        [
            max(float(bbox["x_max"]) - float(bbox["x_min"]), 0.0),
            max(float(bbox["y_max"]) - float(bbox["y_min"]), 0.0),
            max(float(bbox["z_max"]) - float(bbox["z_min"]), 0.0),
        ]
    )
    return {
        "log1p_node_count": math.log1p(node_count),
        "log1p_branch_points": math.log1p(branch_points),
        "log1p_terminal_nodes": math.log1p(terminal_nodes),
        "log1p_cable_length": math.log1p(cable_length),
        "branch_fraction": branch_points / node_count,
        "terminal_fraction": terminal_nodes / node_count,
        "log1p_mean_edge_length": math.log1p(cable_length / edge_count),
        "log1p_bbox_extent_small": math.log1p(extents[0]),
        "log1p_bbox_extent_mid": math.log1p(extents[1]),
        "log1p_bbox_extent_large": math.log1p(extents[2]),
    }


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile of empty values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _robust_location_scale(
    descriptors: list[dict[str, float]],
) -> tuple[dict[str, float], dict[str, float], dict[str, str]]:
    center: dict[str, float] = {}
    scale: dict[str, float] = {}
    scale_method: dict[str, str] = {}
    for feature in FEATURE_NAMES:
        values = [float(row[feature]) for row in descriptors]
        median = statistics.median(values)
        mad = statistics.median([abs(value - median) for value in values])
        robust_scale = MAD_NORMAL_CONSISTENCY * mad
        method = "mad"
        if robust_scale <= ROBUST_SCALE_FLOOR:
            iqr = _percentile(values, 0.75) - _percentile(values, 0.25)
            robust_scale = iqr / IQR_NORMAL_CONSISTENCY
            method = "iqr"
        if robust_scale <= ROBUST_SCALE_FLOOR:
            robust_scale = 1.0
            method = "unit_fallback"
        center[feature] = round(median, 12)
        scale[feature] = round(robust_scale, 12)
        scale_method[feature] = method
    return center, scale, scale_method


def _distance(
    left: dict[str, float],
    right: dict[str, float],
    scale: dict[str, float],
) -> float:
    squared = [
        ((float(left[name]) - float(right[name])) / float(scale[name])) ** 2
        for name in FEATURE_NAMES
    ]
    return math.sqrt(sum(squared) / len(squared))


def build_protocol(records: list[dict[str, Any]]) -> dict[str, Any]:
    canonical = sorted(records, key=lambda row: str(row["body_id"]))
    descriptors = [_descriptor(record["stats"]) for record in canonical]
    center, scale, scale_method = _robust_location_scale(descriptors)

    peer_rows: list[dict[str, Any]] = []
    nearest_distances: list[float] = []
    for index, record in enumerate(canonical):
        descriptor = descriptors[index]
        candidates: list[tuple[float, str]] = []
        for other_index, other in enumerate(canonical):
            if other_index == index:
                continue
            candidates.append(
                (
                    _distance(descriptor, descriptors[other_index], scale),
                    str(other["body_id"]),
                )
            )
        candidates.sort(key=lambda item: (item[0], item[1]))
        nearest_distance, nearest_body_id = candidates[0]
        rounded_descriptor = {
            name: round(float(descriptor[name]), 12) for name in FEATURE_NAMES
        }
        rounded_distance = round(nearest_distance, 12)
        nearest_distances.append(rounded_distance)
        peer_rows.append(
            {
                "body_id": str(record["body_id"]),
                "descriptor": rounded_descriptor,
                "nearest_peer_body_id": nearest_body_id,
                "nearest_peer_distance": rounded_distance,
            }
        )

    threshold = max(nearest_distances)
    return {
        "schema": SCHEMA,
        "target_type": TARGET_TYPE,
        "target_body_excluded": TARGET_BODY_ID,
        "peer_swc_cohort_receipt_sha256": EXPECTED_COHORT_RECEIPT_SHA256,
        "feature_names": list(FEATURE_NAMES),
        "feature_policy": (
            "translation-free coarse topology/geometry descriptors; bbox extents are sorted to "
            "avoid left/right axis-order dependence"
        ),
        "normalization": {
            "policy": "peer-only median plus robust scale",
            "center": center,
            "scale": scale,
            "scale_method": scale_method,
        },
        "distance": {
            "metric": "root-mean-square robust-standardized feature difference",
            "formula": "sqrt(mean(((x_i-y_i)/scale_i)^2))",
        },
        "peer_envelope": {
            "policy": "maximum peer leave-one-out nearest-neighbor distance",
            "acceptance_rule": "target_nearest_peer_distance <= frozen_peer_envelope_threshold",
            "threshold": round(threshold, 12),
            "loo_nearest_peer_distance_min": round(min(nearest_distances), 12),
            "loo_nearest_peer_distance_median": round(statistics.median(nearest_distances), 12),
            "loo_nearest_peer_distance_max": round(max(nearest_distances), 12),
        },
        "peers": peer_rows,
    }


def audit_protocol(
    protocol: dict[str, Any],
    *,
    expected_protocol_receipt_sha256: str | None = EXPECTED_PROTOCOL_RECEIPT_SHA256,
) -> dict[str, Any]:
    digest = _sha256_json(protocol)
    peers = protocol.get("peers", [])
    body_ids = [str(row["body_id"]) for row in peers]
    expected_body_ids = sorted(body_id for body_id, _vfb, _url in PEER_ASSETS)
    threshold = float(protocol["peer_envelope"]["threshold"])
    distances = [float(row["nearest_peer_distance"]) for row in peers]
    structural_gates = {
        "peer_swc_cohort_receipt_is_frozen": EXPECTED_COHORT_RECEIPT_SHA256 is not None,
        "exact_peer_count": len(peers) == len(PEER_ASSETS),
        "peer_body_ids_match_frozen_asset_cohort": body_ids == expected_body_ids,
        "target_body_excluded": TARGET_BODY_ID not in body_ids,
        "exact_predeclared_feature_set": protocol.get("feature_names") == list(FEATURE_NAMES),
        "threshold_is_peer_only_max_loo_nearest_neighbor": bool(distances)
        and math.isclose(threshold, max(distances), rel_tol=0.0, abs_tol=1e-12),
        "target_morphology_not_read": True,
        "current_calibration_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "promotion_remains_blocked": True,
    }
    structural_pass = all(structural_gates.values())
    frozen = expected_protocol_receipt_sha256 is not None
    matches = frozen and digest == expected_protocol_receipt_sha256
    gates = {
        **structural_gates,
        "protocol_receipt_frozen": frozen,
        "protocol_receipt_matches": bool(matches),
    }
    passed = all(gates.values())
    if passed:
        status = STATUS_REVIEW
    elif structural_pass and not frozen:
        status = STATUS_DISCOVERY
    else:
        status = STATUS_FAIL
    return {
        "schema": SCHEMA,
        "status": status,
        "passed": passed,
        "protocol_receipt_sha256": digest,
        "expected_protocol_receipt_sha256": expected_protocol_receipt_sha256,
        "protocol": protocol,
        "target_morphology_compared": False,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "gates": gates,
        "interpretation": (
            "This peer-only protocol freezes a coarse morphology descriptor, robust normalization, "
            "distance metric, and acceptance envelope before body 905407 is evaluated. Passing a "
            "future target audit would mean only that the target falls within this peer-derived "
            "descriptor envelope; it would not prove functional identity or movement tuning."
        ),
    }


def discover() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for body_id, vfb_id, swc_url in PEER_ASSETS:
        payload = _download_bytes(swc_url)
        stats = _stats(_parse_swc(payload))
        records.append({"body_id": body_id, "vfb_id": vfb_id, "swc_url": swc_url, "stats": stats})
    return audit_protocol(build_protocol(records))


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
