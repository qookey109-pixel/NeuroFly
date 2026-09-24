#!/usr/bin/env python3
"""Probe public BANC↔FANC NBLAST review/raw products for root↔cell-ID evidence.

The pinned BANC pipeline computes each raw per-query CSV with BOTH:
- fanc_match: FANC root_id
- cell_id: FANC cell_ids_v2.id

The public compiled feather later collapses the target to match_id=cell_id.
For the frozen BANC SNpp41 query, the compiled candidate is cell_id 20201,
score 0.1, validation=false.

This audit asks whether any public reviewed/raw product still exposes the exact
root_id associated with cell_id 20201, without re-running morphology.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import socket
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
ROOT = f"https://storage.googleapis.com/{BUCKET}"

PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"
PIPELINE_RAW_PATH = "banc/nblast/banc-fanc-nblast.R"
PIPELINE_COMPILE_PATH = "banc/nblast/banc-nblast-compile.R"
PIPELINE_SHARE_PATH = "banc/share/banc-nblast-share-gcs.R"
NBLAST_VERSION = "elastix_tpsreg_240721"

TARGET_BANC_ROOT = "720575941508169089"
TARGET_BANC_SUPERVOXEL = "77060647762534032"
TARGET_FANC_CELL_ID = "20201"
RAW_FILENAME = (
    f"supervoxel_id_{TARGET_BANC_SUPERVOXEL}_"
    f"root_id_{TARGET_BANC_ROOT}.csv"
)

REVIEWED_OBJECT = "nblast/banc_fanc_reviewed_matches.csv"

RAW_CANDIDATE_OBJECTS = (
    f"nblast/fanc/results/{NBLAST_VERSION}/{RAW_FILENAME}",
    f"nblast/fanc/results/{RAW_FILENAME}",
    f"nblast/results/{NBLAST_VERSION}/{RAW_FILENAME}",
    f"nblast/raw/fanc/{NBLAST_VERSION}/{RAW_FILENAME}",
    f"matching/fanc/results/{NBLAST_VERSION}/{RAW_FILENAME}",
    f"fanc/results/{NBLAST_VERSION}/{RAW_FILENAME}",
)

LIST_PREFIXES = (
    "nblast/",
    "nblast/fanc",
    "nblast/raw",
    "matching/fanc",
)

RECEIPT_SCHEMA = "neurofly-public-fanc-raw-nblast-audit-v0.1"
USER_AGENT = "NeuroFly-public-fanc-raw-nblast-audit/0.1"
TIMEOUT = 30

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


def fetch(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            data = res.read()
            return {
                "url": url,
                "http_status": int(res.status),
                "content_type": res.headers.get("Content-Type", ""),
                "byte_count": len(data),
                "error": None,
                "data": data,
            }
    except HTTPError as exc:
        data = exc.read(4096)
        return {
            "url": url,
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "byte_count": len(data),
            "error": f"HTTPError:{exc.code}",
            "body_preview": data.decode("utf-8", errors="replace"),
            "data": None,
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "url": url,
            "http_status": 0,
            "content_type": "",
            "byte_count": 0,
            "error": f"{type(exc).__name__}:{exc}",
            "data": None,
        }


def list_prefix(prefix: str) -> dict[str, Any]:
    url = f"{ROOT}?" + urlencode({"prefix": prefix, "max-keys": 1000})
    result = fetch(url)
    data = result.pop("data", None)
    objects: list[dict[str, Any]] = []
    is_truncated = False
    if data and result.get("http_status") == 200:
        try:
            root = ET.fromstring(data)
            for node in root.iter():
                if node.tag.endswith("Contents"):
                    name = None
                    size = None
                    for child in node:
                        if child.tag.endswith("Key"):
                            name = child.text
                        elif child.tag.endswith("Size"):
                            try:
                                size = int(child.text or "0")
                            except ValueError:
                                size = None
                    if name:
                        objects.append({"name": name, "size": size})
                elif node.tag.endswith("IsTruncated"):
                    is_truncated = (node.text or "").strip().lower() == "true"
        except ET.ParseError as exc:
            result["parse_error"] = f"ET.ParseError:{exc}"
    result.update({
        "prefix": prefix,
        "objects": objects,
        "object_count": len(objects),
        "is_truncated": is_truncated,
    })
    return result


def parse_csv(data: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = [
        {k: (v or "").strip() for k, v in row.items()}
        for row in reader
    ]
    return list(reader.fieldnames or []), rows


def exact_review_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    aliases_query = ("pt_root_id", "query_id", "query_root_id", "root_id")
    out = []
    for row in rows:
        query_values = {row.get(k, "") for k in aliases_query}
        match_value = row.get("match_id", row.get("fanc_match", ""))
        if TARGET_BANC_ROOT in query_values or match_value == TARGET_FANC_CELL_ID:
            out.append(row)
    return out


def inspect_reviewed() -> dict[str, Any]:
    path = REVIEWED_OBJECT
    result = fetch(f"{ROOT}/{path}")
    data = result.pop("data", None)
    out = {"path": path, "fetch": result, "columns": [], "target_rows": []}
    if result.get("http_status") == 200 and data:
        try:
            columns, rows = parse_csv(data)
            out["columns"] = columns
            out["row_count"] = len(rows)
            out["target_rows"] = exact_review_rows(rows)
        except Exception as exc:
            out["parse_error"] = f"{type(exc).__name__}:{exc}"
    return out


def inspect_raw(path: str) -> dict[str, Any]:
    result = fetch(f"{ROOT}/{path}")
    data = result.pop("data", None)
    out: dict[str, Any] = {
        "path": path,
        "fetch": result,
        "columns": [],
        "cell_20201_rows": [],
        "resolved_fanc_roots_for_20201": [],
    }
    if result.get("http_status") != 200 or not data:
        return out

    try:
        columns, rows = parse_csv(data)
        out["columns"] = columns
        out["row_count"] = len(rows)
        target = [
            row for row in rows
            if row.get("cell_id", "") == TARGET_FANC_CELL_ID
            or row.get("match_id", "") == TARGET_FANC_CELL_ID
        ]
        out["cell_20201_rows"] = target[:50]
        roots = sorted({
            row.get("fanc_match", "")
            for row in target
            if row.get("fanc_match", "").isdigit()
        })
        out["resolved_fanc_roots_for_20201"] = roots
    except Exception as exc:
        out["parse_error"] = f"{type(exc).__name__}:{exc}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    listings = [list_prefix(prefix) for prefix in LIST_PREFIXES]
    listed_names = sorted({
        obj["name"]
        for listing in listings
        for obj in listing.get("objects", [])
        if obj.get("name")
    })
    raw_like = [
        name for name in listed_names
        if TARGET_BANC_ROOT in name or RAW_FILENAME in name
    ]

    paths = list(RAW_CANDIDATE_OBJECTS)
    for path in raw_like:
        if path not in paths:
            paths.append(path)

    reviewed = inspect_reviewed()
    raws = [inspect_raw(path) for path in paths]

    existing_raw = [
        item for item in raws
        if item["fetch"].get("http_status") == 200
    ]
    resolved = sorted({
        root
        for item in existing_raw
        for root in item.get("resolved_fanc_roots_for_20201", [])
    })

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "bucket": BUCKET,
            "pipeline_commit": PIPELINE_COMMIT,
            "pipeline_raw_path": PIPELINE_RAW_PATH,
            "pipeline_compile_path": PIPELINE_COMPILE_PATH,
            "pipeline_share_path": PIPELINE_SHARE_PATH,
            "nblast_version": NBLAST_VERSION,
            "reviewed_object": REVIEWED_OBJECT,
            "raw_filename": RAW_FILENAME,
            "raw_candidate_objects": list(RAW_CANDIDATE_OBJECTS),
            "listings": listings,
            "listed_target_like_objects": raw_like,
        },
        "targets": {
            "banc_root": TARGET_BANC_ROOT,
            "banc_supervoxel": TARGET_BANC_SUPERVOXEL,
            "fanc_cell_id": TARGET_FANC_CELL_ID,
        },
        "reviewed_matches": reviewed,
        "raw_object_audits": raws,
        "summary": {
            "reviewed_object_public": reviewed["fetch"].get("http_status") == 200,
            "reviewed_target_row_count": len(reviewed.get("target_rows", [])),
            "public_raw_object_count": len(existing_raw),
            "public_raw_20201_root_mapping_found": bool(resolved),
            "resolved_fanc_roots_for_20201": resolved,
            "interpretation": (
                "A raw CSV mapping would resolve the FANC namespace directly because "
                "the author pipeline stores fanc_match=root_id and cell_id in the same "
                "per-query result. It would not make validation=false a curated match."
            ),
        },
        "locks": LOCKS,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
