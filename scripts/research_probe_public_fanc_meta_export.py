#!/usr/bin/env python3
"""Probe public GCS exports for an exact FANC cell_id <-> root_id mapping.

The BANC pipeline builds fanc_meta.csv locally by joining authoritative
cell_ids_v2 with neuron metadata. The pipeline explicitly defines:

    cell_id = cell_ids_v2.id
    root_id = cell_ids_v2.pt_root_id

A compiled FANC metadata feather is documented as not yet published, but public
GCS layouts can change. This audit checks exact candidate object paths and
public bucket listings without credentials.

Scientific target:
- FANC cell_id 20201 (BANC morphology candidate, validation=false)
- five exact Lee/Phelps hook_flx roots frozen by PR #124

A same-row mapping resolves a namespace only. It does not validate the BANC
morphology match or create a curated FANC->MANC/SNpp41 identity.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import socket
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
GCS_HTTP_ROOT = f"https://storage.googleapis.com/{BUCKET}"

PIPELINE_REPO = "htem/bancpipeline"
PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"
PIPELINE_META_PATH = "fanc/fanc-meta.R"
PIPELINE_PUBLISH_PATH = "banc/transforms/banc-ngl-upload.R"

TARGET_CELL_ID = "20201"
HOOK_FLX_ROOTS = {
    "648518346481857725",
    "648518346509569667",
    "648518346494933426",
    "648518346514448583",
    "648518346494264434",
}

CANDIDATE_OBJECTS = (
    "meta/fanc_meta.csv",
    "meta/fanc_meta.feather",
    "meta/fanc_1116_meta.csv",
    "meta/fanc_1116_meta.feather",
    "compiled_data/fanc_1116/fanc_meta.csv",
    "compiled_data/fanc_1116/fanc_meta.feather",
    "compiled_data/fanc_1116/fanc_1116_meta.csv",
    "compiled_data/fanc_1116/fanc_1116_meta.feather",
    "compiled_data/fanc_1116_meta.csv",
    "compiled_data/fanc_1116_meta.feather",
)

LIST_PREFIXES = (
    "meta/fanc",
    "compiled_data/fanc_1116/",
    "compiled_data/fanc",
)

RECEIPT_SCHEMA = "neurofly-public-fanc-meta-export-audit-v0.1"
USER_AGENT = "NeuroFly-public-fanc-meta-export-audit/0.1"
TIMEOUT = 45
MAX_OBJECT_BYTES = 250 * 1024 * 1024

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


def fetch_bytes(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            data = res.read(MAX_OBJECT_BYTES + 1)
            too_large = len(data) > MAX_OBJECT_BYTES
            if too_large:
                data = data[:MAX_OBJECT_BYTES]
            return {
                "url": url,
                "http_status": int(res.status),
                "content_type": res.headers.get("Content-Type", ""),
                "content_length_header": res.headers.get("Content-Length"),
                "byte_count": len(data),
                "too_large": too_large,
                "error": None,
                "data": data,
            }
    except HTTPError as exc:
        body = exc.read(4096)
        return {
            "url": url,
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "content_length_header": exc.headers.get("Content-Length") if exc.headers else None,
            "byte_count": len(body),
            "too_large": False,
            "error": f"HTTPError:{exc.code}",
            "body_preview": body.decode("utf-8", errors="replace"),
            "data": None,
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "url": url,
            "http_status": 0,
            "content_type": "",
            "content_length_header": None,
            "byte_count": 0,
            "too_large": False,
            "error": f"{type(exc).__name__}:{exc}",
            "data": None,
        }


def list_prefix(prefix: str) -> dict[str, Any]:
    params = urlencode({"prefix": prefix, "max-keys": 1000})
    result = fetch_bytes(f"{GCS_HTTP_ROOT}?{params}")
    data = result.pop("data", None)
    objects: list[dict[str, Any]] = []
    common_prefixes: list[str] = []
    is_truncated = False

    if data and result.get("http_status") == 200:
        try:
            root = ET.fromstring(data)
            for element in root.iter():
                if element.tag.endswith("Contents"):
                    name = None
                    size = None
                    for child in element:
                        if child.tag.endswith("Key"):
                            name = child.text
                        elif child.tag.endswith("Size"):
                            try:
                                size = int(child.text or "0")
                            except ValueError:
                                size = None
                    if name:
                        objects.append({"name": name, "size": size})
                elif element.tag.endswith("CommonPrefixes"):
                    for child in element:
                        if child.tag.endswith("Prefix") and child.text:
                            common_prefixes.append(child.text)
                elif element.tag.endswith("IsTruncated"):
                    is_truncated = (element.text or "").strip().lower() == "true"
        except ET.ParseError as exc:
            result["parse_error"] = f"ET.ParseError:{exc}"

    result.update(
        {
            "prefix": prefix,
            "objects": objects,
            "object_count": len(objects),
            "common_prefixes": sorted(set(common_prefixes)),
            "is_truncated": is_truncated,
        }
    )
    return result


def normalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def row_mapping(row: dict[str, Any]) -> dict[str, str] | None:
    aliases_cell = ("cell_id", "cellid", "fanc_cell_id", "id")
    aliases_root = ("root_id", "pt_root_id", "fanc_root_id")

    cell_key = next((k for k in aliases_cell if k in row), None)
    root_key = next((k for k in aliases_root if k in row), None)
    if cell_key is None or root_key is None:
        return None

    return {
        "cell_key": cell_key,
        "root_key": root_key,
        "cell_id": normalize(row.get(cell_key)),
        "root_id": normalize(row.get(root_key)),
    }


def inspect_rows(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    target_rows: list[dict[str, Any]] = []
    hook_rows: list[dict[str, Any]] = []
    exact_bridge_rows: list[dict[str, Any]] = []
    mappings: list[dict[str, str]] = []

    for row in rows:
        mapping = row_mapping(row)
        if mapping is None:
            continue
        mappings.append(mapping)
        cell_id = mapping["cell_id"]
        root_id = mapping["root_id"]
        compact = {k: normalize(v) for k, v in row.items() if normalize(v)}
        wrapped = {"mapping": mapping, "row": compact}

        if cell_id == TARGET_CELL_ID:
            target_rows.append(wrapped)
        if root_id in HOOK_FLX_ROOTS:
            hook_rows.append(wrapped)
        if cell_id == TARGET_CELL_ID and root_id in HOOK_FLX_ROOTS:
            exact_bridge_rows.append(wrapped)

    return {
        "columns": columns,
        "row_count": len(rows),
        "target_cell_20201_rows": target_rows[:50],
        "hook_flx_root_rows": hook_rows[:100],
        "exact_20201_to_hook_root_rows": exact_bridge_rows[:50],
        "target_cell_20201_found": bool(target_rows),
        "hook_flx_roots_found": sorted(
            {
                item["mapping"]["root_id"]
                for item in hook_rows
                if item["mapping"]["root_id"] in HOOK_FLX_ROOTS
            }
        ),
        "exact_20201_to_hook_root_found": bool(exact_bridge_rows),
    }


def inspect_csv(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(row) for row in reader]
    return inspect_rows(rows, list(reader.fieldnames or []))


def inspect_feather(data: bytes) -> dict[str, Any]:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather

    with tempfile.NamedTemporaryFile(suffix=".feather") as tmp:
        tmp.write(data)
        tmp.flush()
        table = feather.read_table(tmp.name)

    columns = list(table.column_names)
    cell_col = next(
        (c for c in ("cell_id", "cellid", "fanc_cell_id", "id") if c in columns),
        None,
    )
    root_col = next(
        (c for c in ("root_id", "pt_root_id", "fanc_root_id") if c in columns),
        None,
    )

    if cell_col is None or root_col is None:
        return {
            "columns": columns,
            "row_count": int(table.num_rows),
            "error": "missing_cell_or_root_column",
            "target_cell_20201_rows": [],
            "hook_flx_root_rows": [],
            "exact_20201_to_hook_root_rows": [],
            "target_cell_20201_found": False,
            "hook_flx_roots_found": [],
            "exact_20201_to_hook_root_found": False,
        }

    cell_as_str = pc.cast(table[cell_col], pa.string())
    root_as_str = pc.cast(table[root_col], pa.string())

    target_mask = pc.equal(cell_as_str, TARGET_CELL_ID)
    hook_mask = pc.is_in(root_as_str, value_set=pa.array(sorted(HOOK_FLX_ROOTS)))
    target_table = table.filter(target_mask)
    hook_table = table.filter(hook_mask)
    bridge_table = table.filter(pc.and_(target_mask, hook_mask))

    def rows(t: pa.Table, limit: int = 100) -> list[dict[str, Any]]:
        return t.slice(0, limit).to_pylist()

    base = {
        "columns": columns,
        "row_count": int(table.num_rows),
        "target_cell_20201_rows": [
            {"mapping": row_mapping(r), "row": {k: normalize(v) for k, v in r.items() if normalize(v)}}
            for r in rows(target_table, 50)
        ],
        "hook_flx_root_rows": [
            {"mapping": row_mapping(r), "row": {k: normalize(v) for k, v in r.items() if normalize(v)}}
            for r in rows(hook_table, 100)
        ],
        "exact_20201_to_hook_root_rows": [
            {"mapping": row_mapping(r), "row": {k: normalize(v) for k, v in r.items() if normalize(v)}}
            for r in rows(bridge_table, 50)
        ],
        "target_cell_20201_found": target_table.num_rows > 0,
        "hook_flx_roots_found": sorted(
            {
                normalize(v)
                for v in hook_table[root_col].to_pylist()
                if normalize(v) in HOOK_FLX_ROOTS
            }
        ),
        "exact_20201_to_hook_root_found": bridge_table.num_rows > 0,
    }
    return base


def inspect_object(path: str) -> dict[str, Any]:
    url = f"{GCS_HTTP_ROOT}/{path}"
    fetched = fetch_bytes(url)
    data = fetched.pop("data", None)
    result: dict[str, Any] = {
        "path": path,
        "fetch": fetched,
        "table": None,
    }
    if fetched.get("http_status") != 200 or not data:
        return result
    if fetched.get("too_large"):
        result["table"] = {"error": "object_exceeds_probe_limit"}
        return result

    try:
        if path.lower().endswith(".csv"):
            result["table"] = inspect_csv(data)
        elif path.lower().endswith(".feather"):
            result["table"] = inspect_feather(data)
        else:
            result["table"] = {"error": "unsupported_extension"}
    except Exception as exc:
        result["table"] = {"error": f"{type(exc).__name__}:{exc}"}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    listings = [list_prefix(prefix) for prefix in LIST_PREFIXES]
    listed_names = sorted(
        {
            obj["name"]
            for listing in listings
            for obj in listing.get("objects", [])
            if obj.get("name")
        }
    )
    fanc_meta_like = [
        name
        for name in listed_names
        if "fanc" in name.lower()
        and any(token in name.lower() for token in ("meta", "cell_id", "cellid"))
    ]

    paths_to_probe = list(CANDIDATE_OBJECTS)
    for path in fanc_meta_like:
        if path not in paths_to_probe and path.lower().endswith((".csv", ".feather")):
            paths_to_probe.append(path)

    objects = [inspect_object(path) for path in paths_to_probe]
    existing = [
        obj for obj in objects
        if obj["fetch"].get("http_status") == 200
    ]
    parseable = [
        obj for obj in existing
        if isinstance(obj.get("table"), dict)
        and not obj["table"].get("error")
    ]
    target_found = [
        obj for obj in parseable
        if obj["table"].get("target_cell_20201_found")
    ]
    bridge_found = [
        obj for obj in parseable
        if obj["table"].get("exact_20201_to_hook_root_found")
    ]

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "bucket": BUCKET,
            "pipeline_repository": PIPELINE_REPO,
            "pipeline_commit": PIPELINE_COMMIT,
            "pipeline_meta_path": PIPELINE_META_PATH,
            "pipeline_publish_path": PIPELINE_PUBLISH_PATH,
            "candidate_objects": list(CANDIDATE_OBJECTS),
            "list_prefixes": list(LIST_PREFIXES),
            "listings": listings,
            "discovered_fanc_meta_like_objects": fanc_meta_like,
        },
        "targets": {
            "fanc_cell_id": TARGET_CELL_ID,
            "hook_flx_roots": sorted(HOOK_FLX_ROOTS),
        },
        "object_audits": objects,
        "summary": {
            "existing_candidate_object_count": len(existing),
            "parseable_metadata_object_count": len(parseable),
            "cell_id_20201_found_in_public_metadata": bool(target_found),
            "cell_id_20201_source_paths": [obj["path"] for obj in target_found],
            "exact_20201_to_hook_flx_root_found": bool(bridge_found),
            "exact_bridge_source_paths": [obj["path"] for obj in bridge_found],
            "interpretation": (
                "Only exact same-row cell_id/root_id mappings count as namespace "
                "evidence. A mapping cannot validate the BANC morphology candidate "
                "because that BANC->FANC row remains validation=false."
            ),
        },
        "locks": LOCKS,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))

    # Missing public objects are a valid fail-closed result.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
