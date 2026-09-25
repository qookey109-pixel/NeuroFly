#!/usr/bin/env python3
"""Audit public GCS for an exact root->stable-cell-ID provenance bridge.

This deliberately does NOT perform morphology matching. It asks only whether
public objects preserve a direct root identifier, root-named OBJ, or explicit
root/cell-ID manifest that can invert the FANC mesh upload namespace.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
ROOT = f"https://storage.googleapis.com/{BUCKET}"
TIMEOUT = 45
UA = "NeuroFly-public-fanc-provenance-audit/0.1"

HOOK_ROOTS = [
    "648518346476657526",
    "648518346507233352",
    "648518346480125925",
    "648518346514448583",
    "648518346509569667",
    "648518346490237960",
    "648518346496671612",
    "648518346494264434",
    "648518346480666625",
    "648518346494932914",
    "648518346494933426",
    "648518346481857725",
    "648518346517348645",
]

SCAN_PREFIXES = (
    "compiled_data/fanc_1116/",
    "nblast/",
)

OBJ_CANDIDATE_TEMPLATES = (
    "compiled_data/fanc_1116/fanc_banc_space_obj/{root}.obj",
    "compiled_data/fanc_1116/banc_space_obj/{root}.obj",
    "compiled_data/fanc_1116/fanc_banc_space_mesh/{root}.obj",
    "nblast/fanc/banc_space_obj/elastix_tpsreg_240721/{root}.obj",
    "nblast/fanc/banc_space_obj/{root}.obj",
    "nblast/fanc/objects/elastix_tpsreg_240721/{root}.obj",
)

MESH_ROOT = (
    "imported_meshes/fanc_1116_meshes_elastix_tpsreg_240721"
)
SEGPROPS_PATH = f"{MESH_ROOT}/segment_properties/info"
LAYER_INFO_PATH = f"{MESH_ROOT}/info"

LOCKS = {
    "bridge_is_curated_identity": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
}


def fetch(path_or_url: str, max_bytes: int = 16 * 1024 * 1024) -> dict:
    url = path_or_url if path_or_url.startswith("http") else f"{ROOT}/{path_or_url}"
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            data = res.read(max_bytes + 1)
            return {
                "url": url,
                "status": int(res.status),
                "content_type": res.headers.get("Content-Type", ""),
                "too_large": len(data) > max_bytes,
                "data": data[:max_bytes],
                "error": None,
            }
    except HTTPError as exc:
        return {
            "url": url,
            "status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "too_large": False,
            "data": None,
            "error": f"HTTPError:{exc.code}",
        }
    except (URLError, TimeoutError) as exc:
        return {
            "url": url,
            "status": 0,
            "content_type": "",
            "too_large": False,
            "data": None,
            "error": f"{type(exc).__name__}:{exc}",
        }


def list_all(prefix: str) -> dict:
    objects: list[str] = []
    marker: str | None = None
    requests = 0
    while True:
        params = {"prefix": prefix, "max-keys": 1000}
        if marker:
            params["marker"] = marker
        req = fetch(ROOT + "?" + urlencode(params), max_bytes=32 * 1024 * 1024)
        requests += 1
        if req["status"] != 200 or not req["data"]:
            return {
                "prefix": prefix,
                "request_count": requests,
                "objects": objects,
                "error": req["error"] or f"HTTP:{req['status']}",
            }
        root = ET.fromstring(req["data"])
        page: list[str] = []
        truncated = False
        for node in root.iter():
            if node.tag.endswith("Key") and node.text:
                page.append(node.text)
            elif node.tag.endswith("IsTruncated"):
                truncated = (node.text or "").strip().lower() == "true"
        objects.extend(page)
        if not truncated or not page:
            break
        marker = page[-1]
    return {
        "prefix": prefix,
        "request_count": requests,
        "objects": sorted(set(objects)),
        "error": None,
    }


def inspect_json(path: str) -> dict:
    got = fetch(path)
    result = {
        "path": path,
        "status": got["status"],
        "error": got["error"],
        "keys": [],
        "contains_root_property": False,
        "contains_cell_id_property": False,
    }
    if got["status"] == 200 and got["data"]:
        try:
            obj = json.loads(got["data"].decode("utf-8"))
        except Exception as exc:
            result["parse_error"] = f"{type(exc).__name__}:{exc}"
            return result
        result["keys"] = sorted(obj.keys()) if isinstance(obj, dict) else []

        text = json.dumps(obj, sort_keys=True).lower()
        result["contains_root_property"] = any(
            token in text for token in ("root_id", "pt_root_id", "fanc_root")
        )
        result["contains_cell_id_property"] = "cell_id" in text
        if path.endswith("segment_properties/info") and isinstance(obj, dict):
            inline = obj.get("inline", {})
            props = inline.get("properties", []) if isinstance(inline, dict) else []
            result["segment_property_ids"] = [
                p.get("id") for p in props if isinstance(p, dict)
            ]
            result["segment_id_count"] = len(inline.get("ids", [])) if isinstance(inline, dict) and isinstance(inline.get("ids"), list) else None
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    listings = [list_all(prefix) for prefix in SCAN_PREFIXES]
    all_names = sorted(
        {
            name
            for listing in listings
            for name in listing["objects"]
        }
    )

    root_hits = {
        root: [name for name in all_names if root in name]
        for root in HOOK_ROOTS
    }
    root_non_swc_hits = {
        root: [
            name for name in names
            if not name.lower().endswith(".swc")
        ]
        for root, names in root_hits.items()
    }

    explicit_obj_probes = []
    for root in HOOK_ROOTS:
        for template in OBJ_CANDIDATE_TEMPLATES:
            path = template.format(root=root)
            got = fetch(path, max_bytes=1024)
            explicit_obj_probes.append({
                "root": root,
                "path": path,
                "status": got["status"],
                "error": got["error"],
            })

    # Upload code uses stable cell_id as public mesh_id. Probe root-named mesh
    # paths anyway so the public state is directly evidenced.
    root_mesh_probes = []
    for root in HOOK_ROOTS:
        for suffix in (f"meshes/{root}:0", f"meshes/{root}"):
            path = f"{MESH_ROOT}/{suffix}"
            got = fetch(path, max_bytes=1024)
            root_mesh_probes.append({
                "root": root,
                "path": path,
                "status": got["status"],
                "error": got["error"],
            })

    segprops = inspect_json(SEGPROPS_PATH)
    layer_info = inspect_json(LAYER_INFO_PATH)

    obj_positive = [x for x in explicit_obj_probes if x["status"] == 200]
    root_mesh_positive = [x for x in root_mesh_probes if x["status"] == 200]
    non_swc_positive = {
        root: hits for root, hits in root_non_swc_hits.items() if hits
    }

    receipt = {
        "schema": "neurofly-public-fanc-provenance-audit-v0.1",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": {"hook_flx_roots": HOOK_ROOTS},
        "source_contract": {
            "local_mesh_transform_output": "<root_id>.obj",
            "public_mesh_upload_id": "stable FANC cell_id",
            "public_segment_properties_id": "stable FANC cell_id",
            "note": (
                "The BANC pipeline transforms a root-named local OBJ, then uploads "
                "that same mesh under stable cell_id. An explicit public root-named "
                "OBJ/manifest would therefore recover namespace provenance."
            ),
        },
        "listings": [
            {
                "prefix": x["prefix"],
                "request_count": x["request_count"],
                "object_count": len(x["objects"]),
                "error": x["error"],
            }
            for x in listings
        ],
        "root_object_hits": root_hits,
        "root_non_swc_hits": root_non_swc_hits,
        "explicit_root_obj_probes": explicit_obj_probes,
        "root_named_public_mesh_probes": root_mesh_probes,
        "segment_properties": segprops,
        "layer_info": layer_info,
        "summary": {
            "roots_with_any_public_object_name": sum(bool(v) for v in root_hits.values()),
            "roots_with_non_swc_public_object_name": len(non_swc_positive),
            "public_root_named_obj_count": len(obj_positive),
            "public_root_named_mesh_count": len(root_mesh_positive),
            "segment_properties_contains_root_property": segprops["contains_root_property"],
            "exact_public_provenance_bridge_found": bool(
                non_swc_positive or obj_positive or root_mesh_positive or segprops["contains_root_property"]
            ),
            "interpretation": (
                "SWC-only root sightings do not invert the stable-cell-ID mesh namespace. "
                "If no direct root-bearing public object or property exists, exact public "
                "provenance recovery is unavailable and authenticated cell_ids_v2 remains "
                "the authoritative route."
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
