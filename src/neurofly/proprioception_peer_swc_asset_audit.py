from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from neurofly.proprioception_swc_asset_audit import (
    _download_bytes,
    _parse_swc,
    _sha256_bytes,
    _sha256_json,
    _stats,
)


SCHEMA = "neurofly-proprioception-snpp41-peer-swc-asset-audit-v1"
STATUS_DISCOVERY = "DISCOVERY_REQUIRED"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_FAIL = "FAIL"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
FROZEN_SOURCE_INVENTORY_SHA256 = (
    "5c7e7bcf85553c5cda5ae1688d3e66f17121171f7cde87891edce60dc5451f65"
)
EXPECTED_COHORT_RECEIPT_SHA256: str | None = (
    "aeba54052eb7a53c1c1e9b7f6bf1a7fb1010baa3023db9b693af9f3e3e6e70d2"
)

PEER_ASSETS: tuple[tuple[str, str, str], ...] = (
    ("807970", "VFB_jrmc173d", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173d/VFB_00200000/volume.swc"),
    ("808576", "VFB_jrmc173m", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173m/VFB_00200000/volume.swc"),
    ("809027", "VFB_jrmc173n", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173n/VFB_00200000/volume.swc"),
    ("809102", "VFB_jrmc173e", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173e/VFB_00200000/volume.swc"),
    ("809353", "VFB_jrmc173o", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173o/VFB_00200000/volume.swc"),
    ("812228", "VFB_jrmc173h", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173h/VFB_00200000/volume.swc"),
    ("813147", "VFB_jrmc1738", "https://www.virtualflybrain.org/data/VFB/i/jrmc/1738/VFB_00200000/volume.swc"),
    ("813644", "VFB_jrmc173i", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173i/VFB_00200000/volume.swc"),
    ("814628", "VFB_jrmc173j", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173j/VFB_00200000/volume.swc"),
    ("816362", "VFB_jrmc173p", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173p/VFB_00200000/volume.swc"),
    ("816580", "VFB_jrmc173k", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173k/VFB_00200000/volume.swc"),
    ("817154", "VFB_jrmc173a", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173a/VFB_00200000/volume.swc"),
    ("817298", "VFB_jrmc173c", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173c/VFB_00200000/volume.swc"),
    ("819524", "VFB_jrmc1739", "https://www.virtualflybrain.org/data/VFB/i/jrmc/1739/VFB_00200000/volume.swc"),
    ("819559", "VFB_jrmc173g", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173g/VFB_00200000/volume.swc"),
    ("820887", "VFB_jrmc173q", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173q/VFB_00200000/volume.swc"),
    ("822285", "VFB_jrmc173r", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173r/VFB_00200000/volume.swc"),
    ("824107", "VFB_jrmc173l", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173l/VFB_00200000/volume.swc"),
    ("826386", "VFB_jrmc173s", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173s/VFB_00200000/volume.swc"),
    ("911942", "VFB_jrmc173f", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173f/VFB_00200000/volume.swc"),
    ("936031", "VFB_jrmc173t", "https://www.virtualflybrain.org/data/VFB/i/jrmc/173t/VFB_00200000/volume.swc"),
)


def _sha256_json_any(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_asset_record(
    body_id: str,
    vfb_id: str,
    swc_url: str,
    payload: bytes,
) -> dict[str, Any]:
    nodes = _parse_swc(payload)
    stats = _stats(nodes)
    return {
        "body_id": body_id,
        "vfb_id": vfb_id,
        "swc_url": swc_url,
        "swc_sha256": _sha256_bytes(payload),
        "stats": stats,
        "stats_sha256": _sha256_json(stats),
    }


def _canonical_receipt(records: list[dict[str, Any]]) -> dict[str, Any]:
    canonical_records = sorted(
        [
            {
                "body_id": str(record["body_id"]),
                "vfb_id": str(record["vfb_id"]),
                "swc_url": str(record["swc_url"]),
                "swc_sha256": str(record["swc_sha256"]),
                "stats": record["stats"],
                "stats_sha256": str(record["stats_sha256"]),
            }
            for record in records
        ],
        key=lambda record: record["body_id"],
    )
    return {
        "schema": SCHEMA,
        "target_type": TARGET_TYPE,
        "target_body_excluded": TARGET_BODY_ID,
        "source_inventory_sha256": FROZEN_SOURCE_INVENTORY_SHA256,
        "records": canonical_records,
    }


def audit_records(
    records: list[dict[str, Any]],
    *,
    expected_cohort_receipt_sha256: str | None = EXPECTED_COHORT_RECEIPT_SHA256,
) -> dict[str, Any]:
    receipt = _canonical_receipt(records)
    canonical_records = receipt["records"]
    digest = _sha256_json_any(receipt)
    expected_body_ids = sorted(body_id for body_id, _vfb_id, _url in PEER_ASSETS)
    expected_identity = {
        body_id: {"vfb_id": vfb_id, "swc_url": swc_url}
        for body_id, vfb_id, swc_url in PEER_ASSETS
    }
    observed_body_ids = [record["body_id"] for record in canonical_records]

    identity_matches = all(
        record["body_id"] in expected_identity
        and record["vfb_id"] == expected_identity[record["body_id"]]["vfb_id"]
        and record["swc_url"] == expected_identity[record["body_id"]]["swc_url"]
        for record in canonical_records
    )
    sha_shapes_valid = all(
        len(record["swc_sha256"]) == 64
        and len(record["stats_sha256"]) == 64
        and all(character in "0123456789abcdef" for character in record["swc_sha256"])
        and all(character in "0123456789abcdef" for character in record["stats_sha256"])
        for record in canonical_records
    )
    stats_integrity = all(
        _sha256_json(record["stats"]) == record["stats_sha256"]
        for record in canonical_records
    )
    skeletons_valid = all(
        int(record["stats"].get("node_count", 0)) > 0
        and int(record["stats"].get("root_count", 0)) >= 1
        for record in canonical_records
    )

    structural_gates = {
        "exact_peer_count": len(canonical_records) == len(PEER_ASSETS),
        "peer_body_ids_match_frozen_source_inventory": observed_body_ids == expected_body_ids,
        "target_body_excluded": TARGET_BODY_ID not in observed_body_ids,
        "vfb_identity_and_swc_urls_match_frozen_inventory": identity_matches,
        "all_swc_and_stats_sha256_well_formed": sha_shapes_valid,
        "all_stats_receipts_self_consistent": stats_integrity,
        "all_peer_skeletons_nonempty_with_root": skeletons_valid,
    }
    structural_pass = all(structural_gates.values())
    frozen = expected_cohort_receipt_sha256 is not None
    receipt_matches = frozen and digest == expected_cohort_receipt_sha256
    gates = {
        **structural_gates,
        "cohort_receipt_frozen": frozen,
        "cohort_receipt_matches": bool(receipt_matches),
        "peer_morphology_not_compared": True,
        "current_calibration_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "promotion_remains_blocked": True,
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
        "target_type": TARGET_TYPE,
        "target_body_excluded": TARGET_BODY_ID,
        "source_inventory_sha256": FROZEN_SOURCE_INVENTORY_SHA256,
        "peer_count": len(canonical_records),
        "peer_body_ids": observed_body_ids,
        "records": canonical_records,
        "cohort_receipt_sha256": digest,
        "expected_cohort_receipt_sha256": expected_cohort_receipt_sha256,
        "peer_swc_assets_frozen": passed,
        "peer_morphology_compared": False,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "gates": gates,
        "interpretation": (
            "This audit downloads and fingerprints the exact SWC bytes and skeleton statistics "
            "for the 21 frozen SNpp41 peers using the same parser/statistics implementation as "
            "body 905407. It freezes morphology assets only; it does not compare shapes, rank "
            "body 905407, infer extension/flexion tuning, or authorize current/stimulation."
        ),
    }


def discover() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for body_id, vfb_id, swc_url in PEER_ASSETS:
        payload = _download_bytes(swc_url)
        records.append(build_asset_record(body_id, vfb_id, swc_url, payload))
    return audit_records(records)


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
