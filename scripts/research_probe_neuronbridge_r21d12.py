#!/usr/bin/env python3
"""Read-only NeuronBridge probe for the polarity-verified R21D12 hook-flexion driver."""

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
USER_AGENT = "NeuroFly-R21D12-flexion-bridge/0.1"
NEURONBRIDGE_LINE_KEY = "R21D12"
SOURCE_DRIVER = "GMR21D12-GAL4"
FUNCTIONAL_POLARITY = "hook_flexion"
DECISION_POLICY = "evidence_only_no_auto_unlock"

TARGET_BODIES = {
    "SNpp39": [810041, 813911, 814881, 913886],
    "SNpp41": [819524, 819559, 911942],
}


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


def line_name(match: dict[str, Any]) -> str | None:
    for path in (
        ("image", "publishedName"),
        ("image", "publishingName"),
        ("publishedName",),
        ("publishingName",),
        ("line",),
        ("lineName",),
        ("line_name",),
    ):
        value = pick(match, *path)
        if isinstance(value, str) and value:
            return value
    return None


def score_fields(match: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("normalizedScore", "matchingPixels", "matchingRatio", "score"):
        value = match.get(key)
        if value is None:
            value = pick(match, "image", key)
        if value is not None:
            result[key] = value
    for key in ("id", "libraryName", "gender", "objective", "slideCode"):
        value = pick(match, "image", key)
        if value is not None:
            result[f"image.{key}"] = value
    result["image.publishedName"] = line_name(match)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/neuronbridge_r21d12_flexion_bridge.json",
    )
    args = parser.parse_args()

    receipt: dict[str, Any] = {
        "schema": "neurofly-neuronbridge-r21d12-flexion-bridge-v0.1",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "source_driver": SOURCE_DRIVER,
        "neuronbridge_line_key": NEURONBRIDGE_LINE_KEY,
        "functional_polarity": FUNCTIONAL_POLARITY,
        "target_bodies": TARGET_BODIES,
        "current_version": None,
        "direct_line_lookup": {},
        "bodies": {},
        "summary": {},
        "governance": {
            "r21d12_functional_polarity_assumed_from_literature": True,
            "r21d12_to_malecns_body_match_found": False,
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

    line_url = (
        f"{BUCKET}/{quote(version)}/metadata/by_line/"
        f"{quote(NEURONBRIDGE_LINE_KEY, safe='')}.json"
    )
    line_status, line_payload = fetch_json(line_url)
    receipt["direct_line_lookup"] = {
        "url": line_url,
        "http_status": line_status,
        "result_count": (
            len(line_payload.get("results", []))
            if isinstance(line_payload, dict)
            and isinstance(line_payload.get("results"), list)
            else None
        ),
    }

    exact_hits: list[dict[str, Any]] = []
    scanned = 0
    fetched_files = 0

    for systematic_type, body_ids in TARGET_BODIES.items():
        for body_id in body_ids:
            body_key = f"{systematic_type}:{body_id}"
            body_status, body_payload = fetch_json(
                f"{BUCKET}/{quote(version)}/metadata/by_body/{body_id}.json"
            )
            body_out: dict[str, Any] = {
                "systematic_type": systematic_type,
                "body_id": body_id,
                "metadata_http_status": body_status,
                "hits": [],
            }
            receipt["bodies"][body_key] = body_out

            if body_status != 200 or not isinstance(body_payload, dict):
                continue
            results = body_payload.get("results")
            if not isinstance(results, list):
                continue

            selected = [
                r for r in results
                if isinstance(r, dict) and is_male_cns_record(r)
            ]
            if not selected:
                selected = [r for r in results if isinstance(r, dict)]

            for record in selected:
                cds_url = cds_url_for_record(record, config)
                if not cds_url:
                    continue
                cds_status, cds_payload = fetch_json(cds_url)
                if cds_status != 200 or not isinstance(cds_payload, dict):
                    continue
                fetched_files += 1
                matches = cds_payload.get("results")
                if not isinstance(matches, list):
                    continue
                scanned += len(matches)

                for rank, match in enumerate(matches, start=1):
                    if not isinstance(match, dict):
                        continue
                    published = line_name(match)
                    if published is None or published.lower() != NEURONBRIDGE_LINE_KEY.lower():
                        continue
                    hit = {
                        "rank_in_file": rank,
                        "match_fields": score_fields(match),
                    }
                    body_out["hits"].append(hit)
                    exact_hits.append(
                        {
                            "systematic_type": systematic_type,
                            "body_id": body_id,
                            **hit,
                        }
                    )

            if body_out["hits"]:
                body_out["best_hit"] = min(
                    body_out["hits"], key=lambda x: x["rank_in_file"]
                )
            else:
                body_out["best_hit"] = None

    bodies_with_hits = sorted(
        {
            (hit["systematic_type"], hit["body_id"])
            for hit in exact_hits
        }
    )
    receipt["summary"] = {
        "cds_result_files_fetched": fetched_files,
        "cds_match_records_scanned": scanned,
        "exact_r21d12_hit_count": len(exact_hits),
        "bodies_with_exact_r21d12_hits": [
            {"systematic_type": t, "body_id": b}
            for t, b in bodies_with_hits
        ],
        "automatic_unlock_performed": False,
    }
    receipt["governance"]["r21d12_to_malecns_body_match_found"] = bool(exact_hits)

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
