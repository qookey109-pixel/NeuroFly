#!/usr/bin/env python3
"""Reverse-direction NeuronBridge check for frozen R21D12 MCFO candidates.

Direction:
  R21D12 LM image -> CDS results -> MaleCNS EM body

This complements the body->LM probe and remains evidence-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


BUCKET = "https://janelia-neuronbridge-data-prod.s3.us-east-1.amazonaws.com"
USER_AGENT = "NeuroFly-R21D12-reverse-bridge/0.1"
LINE_KEY = "R21D12"
DECISION_POLICY = "evidence_only_no_auto_unlock"

TARGET_BODIES = {
    "SNpp39": [810041, 813911, 814881, 913886],
    "SNpp41": [819524, 819559, 911942],
}

# Exact R21D12 single-cell images recovered in the forward body->LM probe.
CANDIDATE_LM_IMAGE_IDS = [
    "2749246983674789899",
    "2749246991392309259",
    "2749246991170011147",
    "2711773263792439307",
    "2711773160935522315",
    "2711773453295288331",
    "2711773216195477515",
    "2711773214836523019",
]


def fetch_bytes(url: str, *, timeout: int = 45) -> tuple[int, bytes]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as res:
            return int(res.status), res.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()
    except URLError as exc:
        raise RuntimeError(f"network error for {url}: {exc}") from exc


def fetch_text(url: str) -> tuple[int, str]:
    status, body = fetch_bytes(url)
    return status, body.decode("utf-8", errors="replace")


def fetch_json(url: str) -> tuple[int, Any | None]:
    status, text = fetch_text(url)
    if status != 200:
        return status, None
    return status, json.loads(text)


def pick(d: Any, *keys: str) -> Any:
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def record_id(record: dict[str, Any]) -> str | None:
    for path in (("id",), ("image", "id")):
        value = pick(record, *path)
        if value is not None:
            return str(value)
    return None


def cds_url_for_record(record: dict[str, Any], config: dict[str, Any]) -> str | None:
    files = record.get("files") or {}
    if not isinstance(files, dict):
        return None
    rel = files.get("CDSResults")
    store = files.get("store") or record.get("store")
    if not rel or not store:
        return None
    if str(rel).startswith(("http://", "https://")):
        return str(rel)
    prefix = pick(config, "stores", str(store), "prefixes", "CDSResults")
    if not prefix:
        return None
    return f"{prefix}{rel}"


def extract_male_cns_body(match: dict[str, Any]) -> int | None:
    candidates = [
        pick(match, "image", "bodyId"),
        pick(match, "image", "body_id"),
        pick(match, "bodyId"),
        pick(match, "body_id"),
    ]
    for value in candidates:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)

    names = [
        pick(match, "image", "publishedName"),
        pick(match, "image", "publishingName"),
        pick(match, "publishedName"),
        pick(match, "publishingName"),
    ]
    for value in names:
        if not isinstance(value, str):
            continue
        low = value.lower()
        if "male-cns" not in low and "male_cns" not in low:
            continue
        m = re.search(r"(\d+)$", value)
        if m:
            return int(m.group(1))
    return None


def compact_match(match: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path, label in (
        (("image", "publishedName"), "image.publishedName"),
        (("image", "id"), "image.id"),
        (("image", "libraryName"), "image.libraryName"),
        (("normalizedScore",), "normalizedScore"),
        (("matchingPixels",), "matchingPixels"),
        (("matchingRatio",), "matchingRatio"),
        (("score",), "score"),
    ):
        value = pick(match, *path)
        if value is not None:
            out[label] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/neuronbridge_r21d12_reverse_bridge.json",
    )
    args = parser.parse_args()

    status, current = fetch_text(f"{BUCKET}/current.txt")
    if status != 200:
        raise RuntimeError(f"current.txt returned HTTP {status}")
    version = current.strip()

    status, config = fetch_json(f"{BUCKET}/{quote(version)}/config.json")
    if status != 200 or not isinstance(config, dict):
        raise RuntimeError(f"config.json returned HTTP {status}")

    status, line_payload = fetch_json(
        f"{BUCKET}/{quote(version)}/metadata/by_line/{LINE_KEY}.json"
    )
    if status != 200 or not isinstance(line_payload, dict):
        raise RuntimeError(f"by_line/{LINE_KEY}.json returned HTTP {status}")

    line_results = line_payload.get("results")
    if not isinstance(line_results, list):
        raise RuntimeError("R21D12 line payload has no results list")

    wanted = set(CANDIDATE_LM_IMAGE_IDS)
    selected: list[dict[str, Any]] = []
    for record in line_results:
        if not isinstance(record, dict):
            continue
        rid = record_id(record)
        if rid in wanted:
            selected.append(record)

    all_target_ids = {
        body_id
        for body_ids in TARGET_BODIES.values()
        for body_id in body_ids
    }
    type_by_body = {
        body_id: systematic_type
        for systematic_type, body_ids in TARGET_BODIES.items()
        for body_id in body_ids
    }

    image_receipts: dict[str, Any] = {}
    reverse_hits: list[dict[str, Any]] = []

    for record in selected:
        rid = record_id(record)
        assert rid is not None
        entry: dict[str, Any] = {
            "lm_image_id": rid,
            "cds_results_url": None,
            "cds_http_status": None,
            "match_count": None,
            "target_body_hits": [],
        }
        image_receipts[rid] = entry

        cds_url = cds_url_for_record(record, config)
        entry["cds_results_url"] = cds_url
        if not cds_url:
            continue

        cds_status, cds_payload = fetch_json(cds_url)
        entry["cds_http_status"] = cds_status
        if cds_status != 200 or not isinstance(cds_payload, dict):
            continue

        matches = cds_payload.get("results")
        if not isinstance(matches, list):
            continue
        entry["match_count"] = len(matches)

        for rank, match in enumerate(matches, start=1):
            if not isinstance(match, dict):
                continue
            body_id = extract_male_cns_body(match)
            if body_id not in all_target_ids:
                continue
            hit = {
                "rank_in_file": rank,
                "systematic_type": type_by_body[body_id],
                "body_id": body_id,
                "match_fields": compact_match(match),
            }
            entry["target_body_hits"].append(hit)
            reverse_hits.append({"lm_image_id": rid, **hit})

    best_reverse_by_body: dict[str, Any] = {}
    for hit in reverse_hits:
        key = f"{hit['systematic_type']}:{hit['body_id']}"
        prev = best_reverse_by_body.get(key)
        if prev is None or hit["rank_in_file"] < prev["rank_in_file"]:
            best_reverse_by_body[key] = hit

    receipt = {
        "schema": "neurofly-neuronbridge-r21d12-reverse-bridge-v0.1",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "current_version": version,
        "line_key": LINE_KEY,
        "candidate_lm_image_ids": CANDIDATE_LM_IMAGE_IDS,
        "line_result_count": len(line_results),
        "selected_candidate_record_count": len(selected),
        "images": image_receipts,
        "reverse_target_hits": reverse_hits,
        "best_reverse_hit_by_body": best_reverse_by_body,
        "summary": {
            "reverse_target_hit_count": len(reverse_hits),
            "target_bodies_with_reverse_hits": sorted(best_reverse_by_body),
            "automatic_unlock_performed": False,
        },
        "governance": {
            "bidirectional_body_line_bridge_reviewed": True,
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PROBE_ERROR: {exc}", file=sys.stderr)
        raise
