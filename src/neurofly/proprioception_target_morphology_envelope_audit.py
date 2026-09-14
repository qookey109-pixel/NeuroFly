from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from neurofly.proprioception_peer_morphology_protocol import (
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    _descriptor,
    _distance,
    audit_protocol,
    build_protocol,
)
from neurofly.proprioception_peer_swc_asset_audit import PEER_ASSETS
from neurofly.proprioception_swc_asset_audit import (
    EXPECTED_STATS_SHA256,
    EXPECTED_SWC_SHA256,
    SWC_URL,
    TARGET_BODY_ID,
    VFB_ID,
    _download_bytes,
    _parse_swc,
    _sha256_bytes,
    _sha256_json,
    _stats,
)


SCHEMA = "neurofly-proprioception-snpp41-body905407-morphology-envelope-audit-v1"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_FAIL = "FAIL"


def _peer_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for body_id, vfb_id, swc_url in PEER_ASSETS:
        payload = _download_bytes(swc_url)
        records.append(
            {
                "body_id": body_id,
                "vfb_id": vfb_id,
                "swc_url": swc_url,
                "stats": _stats(_parse_swc(payload)),
            }
        )
    return records


def build_report(
    *,
    target_payload: bytes,
    peer_records: list[dict[str, Any]],
) -> dict[str, Any]:
    protocol = build_protocol(peer_records)
    protocol_audit = audit_protocol(
        protocol,
        expected_protocol_receipt_sha256=EXPECTED_PROTOCOL_RECEIPT_SHA256,
    )

    target_stats = _stats(_parse_swc(target_payload))
    target_swc_sha = _sha256_bytes(target_payload)
    target_stats_sha = _sha256_json(target_stats)
    target_descriptor = _descriptor(target_stats)

    scale = protocol["normalization"]["scale"]
    peer_distances: list[tuple[float, str]] = []
    for peer in protocol["peers"]:
        peer_distances.append(
            (
                _distance(target_descriptor, peer["descriptor"], scale),
                str(peer["body_id"]),
            )
        )
    peer_distances.sort(key=lambda item: (item[0], item[1]))
    nearest_distance, nearest_body_id = peer_distances[0]
    threshold = float(protocol["peer_envelope"]["threshold"])
    within_envelope = nearest_distance <= threshold + 1e-12

    gates = {
        "frozen_peer_protocol_reproduces": bool(protocol_audit["passed"]),
        "target_swc_sha_matches_frozen_asset": target_swc_sha == EXPECTED_SWC_SHA256,
        "target_stats_sha_matches_frozen_asset": target_stats_sha == EXPECTED_STATS_SHA256,
        "target_identity_is_exact_body905407": TARGET_BODY_ID == "905407" and VFB_ID == "VFB_jrmc173b",
        "target_compared_with_predeclared_metric": True,
        "target_within_frozen_peer_envelope": within_envelope,
        "current_calibration_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "promotion_remains_blocked": True,
    }
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "status": STATUS_REVIEW if passed else STATUS_FAIL,
        "passed": passed,
        "target": {
            "body_id": TARGET_BODY_ID,
            "vfb_id": VFB_ID,
            "swc_url": SWC_URL,
            "swc_sha256": target_swc_sha,
            "stats_sha256": target_stats_sha,
            "stats": target_stats,
            "descriptor": {key: round(float(value), 12) for key, value in target_descriptor.items()},
        },
        "frozen_protocol_receipt_sha256": EXPECTED_PROTOCOL_RECEIPT_SHA256,
        "peer_envelope_threshold": round(threshold, 12),
        "nearest_peer_body_id": nearest_body_id,
        "nearest_peer_distance": round(nearest_distance, 12),
        "distance_margin_to_threshold": round(threshold - nearest_distance, 12),
        "within_peer_envelope": within_envelope,
        "peer_distance_ranking": [
            {"body_id": body_id, "distance": round(distance, 12)}
            for distance, body_id in peer_distances
        ],
        "gates": gates,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "interpretation": (
            "This audit applies the frozen peer-only coarse morphology protocol to body 905407. "
            "A pass means only that its descriptor lies within the predeclared SNpp41 peer envelope. "
            "It does not establish functional identity, extension/flexion tuning, or authorize current."
        ),
    }


def discover() -> dict[str, Any]:
    return build_report(
        target_payload=_download_bytes(SWC_URL),
        peer_records=_peer_records(),
    )


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
