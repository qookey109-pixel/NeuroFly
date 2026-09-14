from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "neurofly-proprioception-snpp41-peer-morphology-source-inventory-v1"
STATUS_DISCOVERY = "DISCOVERY_REQUIRED"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_FAIL = "FAIL"
VFB_API = "https://v3-cached.virtualflybrain.org"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
PEER_BODY_IDS = (
    "807970",
    "808576",
    "809027",
    "809102",
    "809353",
    "812228",
    "813147",
    "813644",
    "814628",
    "816362",
    "816580",
    "817154",
    "817298",
    "819524",
    "819559",
    "820887",
    "822285",
    "824107",
    "826386",
    "911942",
    "936031",
)
EXPECTED_INVENTORY_SHA256: str | None = None


def _get_json(path: str, params: dict[str, str | int]) -> Any:
    query = urllib.parse.urlencode(params)
    url = f"{VFB_API}{path}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "NeuroFly/0.4 peer-morphology-source-audit",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, nested in value.items():
            yield from _walk(nested, path + (str(key),))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk(nested, path + (str(index),))


def _candidate_vfb_ids(value: Any) -> list[str]:
    found: set[str] = set()
    for _, item in _walk(value):
        if not isinstance(item, str):
            continue
        for token in item.replace("/", " ").replace(":", " ").split():
            cleaned = token.strip(" ,;()[]{}<>\"'")
            if cleaned.startswith("VFB_") and len(cleaned) > 4:
                found.add(cleaned)
    return sorted(found)


def _contains_body_id(value: Any, body_id: str) -> bool:
    """Match exact body accessions; never accept numeric-prefix substrings."""

    for path, item in _walk(value):
        if isinstance(item, (str, int)) and str(item) == body_id:
            return True
        if isinstance(item, str):
            if any(match == body_id for match in re.findall(r"MaleCNS:(\d+)", item)):
                return True
        if path and path[-1].lower() in {"accession", "bodyid", "body_id"}:
            if str(item) == body_id:
                return True
    return False


def _swc_urls(value: Any) -> list[str]:
    found: set[str] = set()
    for _, item in _walk(value):
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text.lower().startswith(("http://", "https://")) and ".swc" in text.lower():
            found.add(text)
    return sorted(found)


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_inventory(
    records: list[dict[str, Any]],
    *,
    expected_inventory_sha256: str | None = EXPECTED_INVENTORY_SHA256,
) -> dict[str, Any]:
    canonical_records = [
        {
            "body_id": str(record["body_id"]),
            "matched_vfb_ids": sorted(str(item) for item in record.get("matched_vfb_ids", [])),
            "swc_urls": sorted(str(item) for item in record.get("swc_urls", [])),
        }
        for record in records
    ]
    canonical_records.sort(key=lambda row: row["body_id"])
    receipt = {
        "schema": SCHEMA,
        "target_type": TARGET_TYPE,
        "target_body_excluded": TARGET_BODY_ID,
        "peer_body_ids": list(PEER_BODY_IDS),
        "records": canonical_records,
    }
    digest = _sha256_json(receipt)

    observed_ids = [row["body_id"] for row in canonical_records]
    exact_identity = all(len(row["matched_vfb_ids"]) == 1 for row in canonical_records)
    every_peer_has_swc = all(bool(row["swc_urls"]) for row in canonical_records)
    structural_gates = {
        "exact_peer_count": len(canonical_records) == len(PEER_BODY_IDS),
        "peer_body_ids_match_frozen_connectivity_receipt": observed_ids == sorted(PEER_BODY_IDS),
        "target_body_excluded": TARGET_BODY_ID not in observed_ids,
        "exact_one_vfb_identity_per_peer": exact_identity,
        "every_peer_has_swc_source": every_peer_has_swc,
    }
    structural_pass = all(structural_gates.values())
    frozen = expected_inventory_sha256 is not None
    matches = frozen and digest == expected_inventory_sha256
    gates = {
        **structural_gates,
        "inventory_receipt_frozen": frozen,
        "inventory_receipt_matches": bool(matches),
        "peer_swc_bytes_not_yet_compared": True,
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
        "peer_count": len(canonical_records),
        "peer_body_ids": observed_ids,
        "records": canonical_records,
        "inventory_sha256": digest,
        "expected_inventory_sha256": expected_inventory_sha256,
        "unresolved_body_ids": [
            row["body_id"] for row in canonical_records if len(row["matched_vfb_ids"]) != 1
        ],
        "peers_without_swc": [row["body_id"] for row in canonical_records if not row["swc_urls"]],
        "peer_morphology_assets_frozen": False,
        "peer_morphology_compared": False,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "gates": gates,
        "interpretation": (
            "This inventory resolves exact public VFB identities and SWC source URLs for the "
            "21 chordotonal SNpp41 peers frozen by the connectivity receipt. It does not freeze "
            "the peer SWC bytes, compare morphology, define a similarity threshold, infer "
            "extension/flexion tuning, or authorize current/stimulation."
        ),
    }


def discover() -> dict[str, Any]:
    # VFB's numeric body-ID search is not guaranteed to index every individual.
    # Therefore use the same two-source discovery policy already validated for
    # body 905407: numeric search plus the systematic type search. Candidates
    # from either path are accepted only if get_term_info contains the exact
    # MaleCNS body accession; no fuzzy identity fallback is permitted.
    type_search = _get_json("/search", {"query": TARGET_TYPE, "limit": 100})
    type_candidate_ids = set(_candidate_vfb_ids(type_search))
    term_cache: dict[str, Any] = {}
    fetch_error_cache: dict[str, str] = {}

    def term_info(vfb_id: str) -> Any | None:
        if vfb_id in term_cache:
            return term_cache[vfb_id]
        if vfb_id in fetch_error_cache:
            return None
        try:
            info = _get_json("/get_term_info", {"id": vfb_id})
        except Exception as exc:
            fetch_error_cache[vfb_id] = f"{type(exc).__name__}:{exc}"
            return None
        term_cache[vfb_id] = info
        return info

    records: list[dict[str, Any]] = []
    for body_id in PEER_BODY_IDS:
        body_search = _get_json("/search", {"query": body_id, "limit": 50})
        body_candidate_ids = set(_candidate_vfb_ids(body_search))
        candidate_ids = sorted(body_candidate_ids | type_candidate_ids)
        matched: list[str] = []
        swc: set[str] = set()
        fetch_errors: list[str] = []
        for vfb_id in candidate_ids:
            info = term_info(vfb_id)
            if info is None:
                if vfb_id in fetch_error_cache:
                    fetch_errors.append(f"{vfb_id}:{fetch_error_cache[vfb_id]}")
                continue
            if _contains_body_id(info, body_id):
                matched.append(vfb_id)
                swc.update(_swc_urls(info))
        records.append(
            {
                "body_id": body_id,
                "body_search_candidate_vfb_ids": sorted(body_candidate_ids),
                "type_search_candidate_vfb_ids": sorted(type_candidate_ids),
                "candidate_vfb_ids": candidate_ids,
                "matched_vfb_ids": sorted(set(matched)),
                "swc_urls": sorted(swc),
                "fetch_errors": sorted(set(fetch_errors)),
            }
        )
    report = audit_inventory(records)
    report["vfb_api"] = VFB_API
    report["discovery_policy"] = "exact-body-search-union-exact-snpp41-type-search"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = discover()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
