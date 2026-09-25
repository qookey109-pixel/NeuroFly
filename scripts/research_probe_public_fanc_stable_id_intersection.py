#!/usr/bin/env python3
"""Intersect public FANC stable-ID annotations with BANC SNpp41 FANC candidates.

No credentials are used. The probe reads only public GCS objects.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
ROOT = f"https://storage.googleapis.com/{BUCKET}"
SEGPROPS = (
    ROOT
    + "/imported_meshes/fanc_1116_meshes_elastix_tpsreg_240721/"
      "segment_properties/info"
)
TARGET_BANC_ROOT = "720575941508169089"
TARGET_FANC_CELL_ID = "20201"
TIMEOUT = 60
UA = "NeuroFly-public-stable-id-intersection/0.1"

LOCKS = {
    "bridge_is_curated_identity": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
}


def fetch(url: str, limit: int = 800 * 1024 * 1024) -> dict:
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            data = res.read(limit + 1)
            return {
                "url": url,
                "status": int(res.status),
                "too_large": len(data) > limit,
                "data": data[:limit],
                "error": None,
            }
    except HTTPError as exc:
        return {"url": url, "status": int(exc.code), "data": None, "error": f"HTTPError:{exc.code}", "too_large": False}
    except (URLError, TimeoutError) as exc:
        return {"url": url, "status": 0, "data": None, "error": f"{type(exc).__name__}:{exc}", "too_large": False}


def list_prefix(prefix: str) -> list[str]:
    names: list[str] = []
    token: str | None = None
    while True:
        params = {"prefix": prefix, "max-keys": 1000}
        if token:
            params["marker"] = token
        result = fetch(ROOT + "?" + urlencode(params), limit=20 * 1024 * 1024)
        if result["status"] != 200 or not result["data"]:
            break
        root = ET.fromstring(result["data"])
        page: list[str] = []
        truncated = False
        for e in root.iter():
            if e.tag.endswith("Key") and e.text:
                page.append(e.text)
            elif e.tag.endswith("IsTruncated"):
                truncated = (e.text or "").strip().lower() == "true"
        names.extend(page)
        if not truncated or not page:
            break
        token = page[-1]
    return sorted(set(names))


def parse_segment_properties(data: bytes) -> tuple[dict[str, dict], set[str], set[str]]:
    obj = json.loads(data.decode("utf-8"))
    inline = obj["inline"]
    ids = [str(x) for x in inline["ids"]]
    props = {p["id"]: p for p in inline["properties"]}
    labels = props.get("label", {}).get("values", [""] * len(ids))
    tag_prop = props.get("tags", {})
    global_tags = [str(x) for x in tag_prop.get("tags", [])]
    tag_values = tag_prop.get("values", [[] for _ in ids])

    rows: dict[str, dict] = {}
    exact_hook: set[str] = set()
    broader: set[str] = set()
    tokens = ("hook", "chordotonal", "sensory", "proprio", "mechanosens", "feco")

    for i, cell_id in enumerate(ids):
        label = str(labels[i]) if i < len(labels) else ""
        raw_idx = tag_values[i] if i < len(tag_values) else []
        tags = []
        if isinstance(raw_idx, list):
            for x in raw_idx:
                try:
                    idx = int(x)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx < len(global_tags):
                    tags.append(global_tags[idx])
        text = " | ".join([label, *tags]).lower()
        row = {"cell_id": cell_id, "label": label, "tags": tags}
        rows[cell_id] = row
        if label.strip().lower() == "hook_flx" or any(str(t).strip().lower() == "hook_flx" for t in tags):
            exact_hook.add(cell_id)
        if any(tok in text for tok in tokens):
            broader.add(cell_id)
    return rows, exact_hook, broader


def inspect_feather(data: bytes, annotation_rows: dict[str, dict], exact_hook: set[str], broader: set[str]) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather

    with tempfile.NamedTemporaryFile(suffix=".feather") as tmp:
        tmp.write(data)
        tmp.flush()
        table = feather.read_table(tmp.name)

    cols = table.column_names
    query_col = "query_root_id" if "query_root_id" in cols else ("query_id" if "query_id" in cols else None)
    pt_col = "pt_root_id" if "pt_root_id" in cols else None
    match_col = "match_id" if "match_id" in cols else None
    score_col = "score" if "score" in cols else None
    val_col = "validation" if "validation" in cols else ("valid" if "valid" in cols else None)

    if not match_col or (not query_col and not pt_col):
        return {"columns": cols, "error": "missing_required_columns"}

    masks = []
    if query_col:
        masks.append(pc.equal(pc.cast(table[query_col], pa.string()), TARGET_BANC_ROOT))
    if pt_col:
        masks.append(pc.equal(pc.cast(table[pt_col], pa.string()), TARGET_BANC_ROOT))
    mask = masks[0]
    for m in masks[1:]:
        mask = pc.or_(mask, m)
    sub = table.filter(mask)

    rows = []
    for raw in sub.to_pylist():
        match_id = "" if raw.get(match_col) is None else str(raw.get(match_col))
        anno = annotation_rows.get(match_id)
        rows.append({
            "match_id": match_id or None,
            "score": raw.get(score_col) if score_col else None,
            "validation": raw.get(val_col) if val_col else None,
            "public_annotation": anno,
            "exact_hook_flx_public_annotation": match_id in exact_hook,
            "broader_feco_sensory_public_annotation": match_id in broader,
        })
    rows.sort(key=lambda r: (r["score"] is not None, r["score"] if r["score"] is not None else -1), reverse=True)

    return {
        "columns": cols,
        "target_row_count": len(rows),
        "target_rows": rows,
        "exact_hook_intersections": [r for r in rows if r["exact_hook_flx_public_annotation"]],
        "broader_intersections": [r for r in rows if r["broader_feco_sensory_public_annotation"]],
        "candidate_20201": next((r for r in rows if r["match_id"] == TARGET_FANC_CELL_ID), None),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    seg = fetch(SEGPROPS, limit=100 * 1024 * 1024)
    if seg["status"] != 200 or not seg["data"]:
        raise SystemExit(f"segment properties unavailable: {seg['status']} {seg['error']}")
    annotations, exact_hook, broader = parse_segment_properties(seg["data"])

    names = list_prefix("nblast/")
    feather_names = [
        n for n in names
        if n.lower().endswith(".feather") and "fanc" in n.lower()
    ]

    audits = []
    for name in feather_names:
        got = fetch(ROOT + "/" + name)
        if got["status"] != 200 or not got["data"] or got["too_large"]:
            audits.append({"path": name, "fetch_status": got["status"], "error": got["error"], "too_large": got["too_large"]})
            continue
        try:
            inspected = inspect_feather(got["data"], annotations, exact_hook, broader)
        except Exception as exc:
            inspected = {"error": f"{type(exc).__name__}:{exc}"}
        audits.append({"path": name, "fetch_status": got["status"], "inspection": inspected})

    positive_exact = []
    positive_broad = []
    for audit in audits:
        ins = audit.get("inspection") or {}
        if ins.get("exact_hook_intersections"):
            positive_exact.append(audit["path"])
        if ins.get("broader_intersections"):
            positive_broad.append(audit["path"])

    receipt = {
        "schema": "neurofly-public-fanc-stable-id-intersection-v0.1",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": {
            "banc_root": TARGET_BANC_ROOT,
            "candidate_cell_id": TARGET_FANC_CELL_ID,
        },
        "segment_properties": {
            "url": SEGPROPS,
            "stable_id_count": len(annotations),
            "exact_hook_flx_stable_ids": sorted(exact_hook, key=lambda x: int(x) if x.isdigit() else x),
            "exact_hook_flx_count": len(exact_hook),
            "broader_feco_sensory_stable_ids": sorted(broader, key=lambda x: int(x) if x.isdigit() else x),
            "broader_feco_sensory_count": len(broader),
            "candidate_20201": annotations.get(TARGET_FANC_CELL_ID),
        },
        "public_nblast": {
            "listed_fanc_feathers": feather_names,
            "audits": audits,
            "exact_hook_intersection_source_paths": positive_exact,
            "broader_intersection_source_paths": positive_broad,
        },
        "interpretation": (
            "An intersection is annotation context for an existing BANC morphology candidate, "
            "not a curated cross-dataset identity. A validation=false row remains unvalidated."
        ),
        "locks": LOCKS,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
