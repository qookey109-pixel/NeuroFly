from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "neurofly-proprioception-snpp41-morphology-source-audit-v1"
STATUS_DISCOVERY = "DISCOVERY_REQUIRED"
STATUS_REVIEW = "REVIEW_REQUIRED"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
VFB_API = "https://v3-cached.virtualflybrain.org"
EXPECTED_VFB_ID: str | None = None
EXPECTED_SOURCE_SHA256: str | None = None


def _get_json(path: str, params: dict[str, str | int]) -> Any:
    query = urllib.parse.urlencode(params)
    url = f"{VFB_API}{path}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "NeuroFly/0.4 morphology-source-audit",
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
        if isinstance(item, str):
            for token in item.replace("/", " ").replace(":", " ").split():
                if token.startswith("VFB_") and len(token) > 4:
                    found.add(token.strip(" ,;()[]{}<>\"'"))
    return sorted(found)


def _contains_target_accession(value: Any) -> bool:
    for path, item in _walk(value):
        if isinstance(item, (str, int)) and str(item) == TARGET_BODY_ID:
            return True
        if isinstance(item, str) and f"MaleCNS:{TARGET_BODY_ID}" in item:
            return True
        if path and path[-1].lower() in {"accession", "bodyid", "body_id"}:
            if str(item) == TARGET_BODY_ID:
                return True
    return False


def _morphology_hints(value: Any) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    terms = ("skeleton", "swc", "mesh", "obj", "pointcloud", "nrrd", "image")
    for path, item in _walk(value):
        if not isinstance(item, str):
            continue
        lowered = item.lower()
        if any(term in lowered for term in terms):
            hints.append({"path": ".".join(path), "value": item})
    hints.sort(key=lambda row: (row["path"], row["value"]))
    return hints


def _canonical_source_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report["schema"],
        "target_body_id": report["target_body_id"],
        "target_type": report["target_type"],
        "matched_vfb_ids": report["matched_vfb_ids"],
        "candidate_term_summaries": report["candidate_term_summaries"],
    }


def _sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_report(
    *,
    search_body: Any,
    search_type: Any,
    term_info_by_id: dict[str, Any],
    expected_vfb_id: str | None = EXPECTED_VFB_ID,
    expected_source_sha256: str | None = EXPECTED_SOURCE_SHA256,
) -> dict[str, Any]:
    candidate_ids = sorted(
        set(_candidate_vfb_ids(search_body)) | set(_candidate_vfb_ids(search_type))
    )
    summaries: list[dict[str, Any]] = []
    matched: list[str] = []
    for vfb_id in candidate_ids:
        info = term_info_by_id.get(vfb_id)
        if info is None:
            continue
        contains_target = _contains_target_accession(info)
        if contains_target:
            matched.append(vfb_id)
        summaries.append(
            {
                "vfb_id": vfb_id,
                "contains_target_accession": contains_target,
                "morphology_hints": _morphology_hints(info),
            }
        )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": STATUS_DISCOVERY,
        "target_body_id": TARGET_BODY_ID,
        "target_type": TARGET_TYPE,
        "vfb_api": VFB_API,
        "candidate_vfb_ids": candidate_ids,
        "matched_vfb_ids": sorted(matched),
        "candidate_term_summaries": summaries,
        "expected_vfb_id": expected_vfb_id,
        "expected_source_sha256": expected_source_sha256,
        "morphology_evidence_present": False,
        "connectivity_is_not_morphology": True,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
    }
    source_sha = _sha256_payload(_canonical_source_payload(report))
    report["source_sha256"] = source_sha
    report["gates"] = {
        "exact_one_vfb_match": len(matched) == 1,
        "vfb_id_frozen": expected_vfb_id is not None,
        "vfb_id_matches": len(matched) == 1 and matched[0] == expected_vfb_id,
        "source_receipt_frozen": expected_source_sha256 is not None,
        "source_receipt_matches": source_sha == expected_source_sha256,
        "current_calibration_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "promotion_remains_blocked": True,
    }
    passed = all(report["gates"].values())
    report["passed"] = passed
    if passed:
        report["status"] = STATUS_REVIEW
        report["morphology_evidence_present"] = True
    return report


def discover() -> dict[str, Any]:
    search_body = _get_json("/search", {"query": TARGET_BODY_ID, "limit": 50})
    search_type = _get_json("/search", {"query": TARGET_TYPE, "limit": 100})
    candidate_ids = sorted(
        set(_candidate_vfb_ids(search_body)) | set(_candidate_vfb_ids(search_type))
    )
    term_info_by_id: dict[str, Any] = {}
    for vfb_id in candidate_ids:
        try:
            term_info_by_id[vfb_id] = _get_json("/get_term_info", {"id": vfb_id})
        except Exception as exc:  # evidence report should preserve partial discovery
            term_info_by_id[vfb_id] = {"audit_fetch_error": f"{type(exc).__name__}: {exc}"}
    return build_report(
        search_body=search_body,
        search_type=search_type,
        term_info_by_id=term_info_by_id,
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
