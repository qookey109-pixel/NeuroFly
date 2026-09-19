#!/usr/bin/env python3
"""Read-only NeuronBridge body-level probe for the FeCO hook polarity gate.

This script follows the public NeuronBridge Python client's data path:
  current.txt -> config.json -> metadata/by_body/<body_id>.json -> CDSResults

It writes evidence only. It never changes NeuroFly runtime/calibration state.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


BUCKET = "https://janelia-neuronbridge-data-prod.s3.us-east-1.amazonaws.com"
USER_AGENT = "NeuroFly-FeCO-evidence-probe/0.1"

# VFB records explicitly expose the same body ID in male-cns:v0.9 and v1.0.
TARGET_BODIES = {
    "SNpp39": [810041, 813911, 814881, 913886],
    "SNpp41": [819524, 819559, 911942],
}

DRIVER_GROUPS = {
    "hook_extension": [
        "VT018774",
        "VT040547",
        "VT018774-p65ADZ",
        "VT040547-GAL4.DBD",
    ],
    "hook_flexion": [
        "VT038873",
        "R32H08",
        "GMR21D12",
        "VT038873-p65ADZ",
        "R32H08-GAL4.DBD",
        "GMR21D12-GAL4",
    ],
}

DIRECT_LINE_LOOKUPS = [
    "VT018774",
    "VT040547",
    "VT018774-p65ADZ",
    "VT040547-GAL4.DBD",
    "VT038873",
    "R32H08",
    "GMR21D12",
    "VT038873-p65ADZ",
    "R32H08-GAL4.DBD",
    "GMR21D12-GAL4",
]

DECISION_POLICY = "evidence_only_no_auto_unlock"


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


def first_nonempty(d: dict[str, Any], paths: list[tuple[str, ...]]) -> Any:
    for path in paths:
        value = pick(d, *path)
        if value not in (None, "", [], {}):
            return value
    return None


def collect_named_fields(value: Any, *, prefix: str = "") -> dict[str, Any]:
    """Keep compact identity/ranking fields without copying huge result payloads."""
    wanted = {
        "id",
        "name",
        "line",
        "lineName",
        "line_name",
        "publishedName",
        "publishingName",
        "bodyId",
        "body_id",
        "libraryName",
        "library",
        "dataset",
        "score",
        "normalizedScore",
        "matchingPixels",
        "matchingRatio",
        "rank",
        "gender",
        "slideCode",
        "objective",
    }
    out: dict[str, Any] = {}

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                child = f"{path}.{k}" if path else k
                if k in wanted and not isinstance(v, (dict, list)):
                    out[child] = v
                elif isinstance(v, (dict, list)):
                    walk(v, child)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj[:4]):
                walk(item, f"{path}[{idx}]")

    walk(value, prefix)
    return out


def token_hits(value: Any) -> dict[str, list[str]]:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False).lower()
    hits: dict[str, list[str]] = {}
    for direction, tokens in DRIVER_GROUPS.items():
        matched = [token for token in tokens if token.lower() in raw]
        if matched:
            hits[direction] = sorted(set(matched))
    return hits


def is_male_cns_record(record: dict[str, Any]) -> bool:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False).lower()
    return "male_cns" in raw or "male-cns" in raw or "flyem_male_cns" in raw


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/neuronbridge_feco_body_probe.json",
        help="JSON evidence receipt path",
    )
    args = parser.parse_args()

    receipt: dict[str, Any] = {
        "schema": "neurofly-neuronbridge-feco-body-probe-v0.1",
        "status": "EVIDENCE_PROBE_ONLY",
        "decision_policy": DECISION_POLICY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bucket": BUCKET,
        "target_bodies": TARGET_BODIES,
        "driver_groups": DRIVER_GROUPS,
        "current_version": None,
        "male_cns_stores": {},
        "direct_line_lookups": {},
        "bodies": {},
        "summary": {},
        "governance": {
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
        },
    }

    status, current = fetch_text(f"{BUCKET}/current.txt")
    if status != 200:
        raise RuntimeError(f"current.txt returned HTTP {status}")
    version = current.strip()
    receipt["current_version"] = version

    status, config = fetch_json(f"{BUCKET}/{quote(version)}/config.json")
    if status != 200 or not isinstance(config, dict):
        raise RuntimeError(f"config.json returned HTTP {status}")

    stores = config.get("stores") or {}
    for key, value in stores.items():
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False).lower()
        if "male_cns" in raw or "male-cns" in raw or "flyem_male_cns" in raw:
            receipt["male_cns_stores"][key] = {
                "label": value.get("label") if isinstance(value, dict) else None,
                "anatomicalArea": value.get("anatomicalArea") if isinstance(value, dict) else None,
                "emLibraries": pick(value, "customSearch", "emLibraries"),
            }

    # Probe exact/partial published line names directly. 404 is evidence of
    # lookup-key absence only, not biological absence.
    for line in DIRECT_LINE_LOOKUPS:
        url = f"{BUCKET}/{quote(version)}/metadata/by_line/{quote(line, safe='')}.json"
        line_status, line_payload = fetch_json(url)
        receipt["direct_line_lookups"][line] = {
            "http_status": line_status,
            "result_count": (
                len(line_payload.get("results", []))
                if isinstance(line_payload, dict)
                and isinstance(line_payload.get("results"), list)
                else None
            ),
        }

    total_cds_files = 0
    total_match_records = 0
    exact_hits: list[dict[str, Any]] = []

    for systematic_type, body_ids in TARGET_BODIES.items():
        for body_id in body_ids:
            body_key = f"{systematic_type}:{body_id}"
            body_url = f"{BUCKET}/{quote(version)}/metadata/by_body/{body_id}.json"
            body_status, body_payload = fetch_json(body_url)
            body_receipt: dict[str, Any] = {
                "systematic_type": systematic_type,
                "body_id": body_id,
                "metadata_http_status": body_status,
                "metadata_result_count": 0,
                "male_cns_record_count": 0,
                "records": [],
            }
            receipt["bodies"][body_key] = body_receipt

            if body_status != 200 or not isinstance(body_payload, dict):
                continue

            results = body_payload.get("results")
            if not isinstance(results, list):
                continue
            body_receipt["metadata_result_count"] = len(results)
            selected = [r for r in results if isinstance(r, dict) and is_male_cns_record(r)]
            if not selected:
                selected = [r for r in results if isinstance(r, dict)]
            body_receipt["male_cns_record_count"] = sum(
                1 for r in results if isinstance(r, dict) and is_male_cns_record(r)
            )

            for record in selected:
                record_summary: dict[str, Any] = {
                    "identity": collect_named_fields(record),
                    "cds_results_url": None,
                    "cds_http_status": None,
                    "cds_match_count": None,
                    "driver_token_hits": [],
                }
                body_receipt["records"].append(record_summary)

                cds_url = cds_url_for_record(record, config)
                record_summary["cds_results_url"] = cds_url
                if not cds_url:
                    continue

                total_cds_files += 1
                cds_status, cds_payload = fetch_json(cds_url)
                record_summary["cds_http_status"] = cds_status
                if cds_status != 200 or not isinstance(cds_payload, dict):
                    continue

                matches = cds_payload.get("results")
                if not isinstance(matches, list):
                    continue
                record_summary["cds_match_count"] = len(matches)
                total_match_records += len(matches)

                for rank, match in enumerate(matches, start=1):
                    hits = token_hits(match)
                    if not hits:
                        continue
                    hit = {
                        "rank_in_file": rank,
                        "directions": hits,
                        "match_fields": collect_named_fields(match),
                    }
                    record_summary["driver_token_hits"].append(hit)
                    exact_hits.append(
                        {
                            "systematic_type": systematic_type,
                            "body_id": body_id,
                            **hit,
                        }
                    )

    receipt["summary"] = {
        "cds_result_files_fetched": total_cds_files,
        "cds_match_records_scanned": total_match_records,
        "exact_driver_token_hit_count": len(exact_hits),
        "exact_driver_token_hits": exact_hits,
        "automatic_unlock_performed": False,
        "interpretation": (
            "Computed/body-level matches are preserved as evidence only. "
            "Any polarity promotion requires separate scientific review of "
            "dataset identity, driver identity, match rank/score, and direction consistency."
        ),
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
