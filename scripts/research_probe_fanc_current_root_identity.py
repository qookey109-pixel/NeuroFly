#!/usr/bin/env python3
"""Read-only FANC legacy CATMAID -> current root identity audit.

Uses the public, author-pinned Phelps/GridTape FANC-space SWCs, the official
FANC v3->v4 transform-service workflow, the official FANC supervoxel lookup
service, and CAVE chunkedgraph get_roots(). It does not perform morphology
matching and never promotes a dominant segmentation root to curated identity.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import socket
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


AUTHOR_REPO = "htem/GridTape_VNC_paper"
AUTHOR_COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
RAW_BASE = f"https://raw.githubusercontent.com/{AUTHOR_REPO}/{AUTHOR_COMMIT}"

LEGACY_FANC_SKIDS = [25849, 25842, 25856, 24831, 25909]
SWC_PATHS = {
    skid: (
        "neuron_reconstructions/skeletons_in_FANC_space/sensory_neurons/"
        f"left T1 leg nerve hook chordotonal sensory neuron (neuron {skid}).swc"
    )
    for skid in LEGACY_FANC_SKIDS
}

FANC_DATASTACK = "fanc_production_mar2021"
VFB_BASE = "https://v3-cached.virtualflybrain.org"
VFB_FANC_XREF_DBS = ("catmaid_fanc", "catmaid_fanc_JRC2018VF")
FANC_CHUNKEDGRAPH_BASE = "https://cave.fanc-fly.com/segmentation/api/v1"
FANC_CHUNKEDGRAPH_TABLE = "mar2021_prod"
FANC_V4_TO_V3_BASE = (
    "https://catmaid3.hms.harvard.edu/services/transform-service/"
    "dataset/fanc_v4_to_v3/s/2"
)
FANC_SVID_LOOKUP = (
    "https://catmaid3.hms.harvard.edu/services/transform-service/query/"
    "dataset/fanc_v4/s/2/values_array_string_response"
)

VOXEL_NM = (4.3, 4.3, 45.0)
SAMPLE_POINTS = 48
RECEIPT_SCHEMA = "neurofly-fanc-current-root-audit-v0.5"
DECISION_POLICY = "evidence_only_no_auto_unlock"
USER_AGENT = "NeuroFly-fanc-current-root-audit/0.5"
TIMEOUT = 25

TARGET_MALECNS_BODY = 911942
TARGET_MANC_BODY = 97015
TARGET_TYPE = "SNpp41"

# Explicit namespace guard: these are CATMAID skeleton IDs, not MANC body IDs
# or MaleCNS body IDs even when decimal values happen to collide.
ID_NAMESPACE = "FANC_Phelps_CATMAID_project2_skeleton"


def fetch(url: str, *, payload: dict[str, Any] | None = None) -> tuple[int, bytes | None, str | None]:
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Content-Type": "application/json",
        },
        method="POST" if payload is not None else "GET",
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            return int(res.status), res.read(), None
    except HTTPError as exc:
        return int(exc.code), exc.read(), f"HTTPError:{exc.code}"
    except (URLError, TimeoutError, socket.timeout) as exc:
        return 0, None, f"{type(exc).__name__}:{exc}"


def fetch_text(url: str) -> tuple[int, str | None, str | None]:
    status, raw, error = fetch(url)
    return status, raw.decode("utf-8", errors="replace") if raw else None, error


def post_json(url: str, payload: dict[str, Any]) -> tuple[int, Any | None, str | None]:
    status, raw, error = fetch(url, payload=payload)
    if raw is None:
        return status, None, error
    try:
        return status, json.loads(raw.decode("utf-8", errors="replace")), error
    except json.JSONDecodeError:
        return status, {"raw_preview": raw[:1000].decode("utf-8", errors="replace")}, error or "JSONDecodeError"


def get_json(url: str) -> tuple[int, Any | None, str | None]:
    status, raw, error = fetch(url)
    if raw is None:
        return status, None, error
    try:
        return status, json.loads(raw.decode("utf-8", errors="replace")), error
    except json.JSONDecodeError:
        return status, {"raw_preview": raw[:1000].decode("utf-8", errors="replace")}, error or "JSONDecodeError"


def vfb_xref_probe(accession: int) -> dict[str, Any]:
    from urllib.parse import urlencode

    # Unfiltered reverse lookup is collision-audit evidence only. External
    # accessions are not globally unique across connectome databases.
    broad_url = f"{VFB_BASE}/xref?" + urlencode({"accession": str(accession)})
    broad_status, broad_payload, broad_error = get_json(broad_url)
    broad_raw = (
        json.dumps(broad_payload, ensure_ascii=False, sort_keys=True)
        if broad_payload is not None else ""
    )

    filtered = {}
    fanc_rows = []
    fanc_vfb_ids = set()
    for db in VFB_FANC_XREF_DBS:
        url = f"{VFB_BASE}/xref?" + urlencode({
            "accession": str(accession),
            "db": db,
        })
        status, payload, error = get_json(url)
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        safe_rows = [r for r in rows if isinstance(r, dict)]
        filtered[db] = {
            "url": url,
            "http_status": status,
            "error": error,
            "rows": safe_rows,
            "count": len(safe_rows),
        }
        for row in safe_rows:
            # Require the returned row itself to name the requested FANC db.
            if str(row.get("db", "")) == db or str(row.get("site_id", "")) == db:
                fanc_rows.append(row)
                vid = row.get("id")
                if isinstance(vid, str) and vid.startswith("VFB_"):
                    fanc_vfb_ids.add(vid)

    terms = {}
    signal_terms = {}
    for vfb_id in sorted(fanc_vfb_ids):
        term_url = f"{VFB_BASE}/get_term_info?" + urlencode({"id": vfb_id})
        ts, tp, te = get_json(term_url)
        traw = json.dumps(tp, ensure_ascii=False, sort_keys=True) if tp is not None else ""
        signals = [
            token for token in ("FANC", "MANC", "MaleCNS", "BANC", "SNpp41", "97015")
            if token.lower() in traw.lower()
        ]
        terms[vfb_id] = {
            "url": term_url,
            "http_status": ts,
            "error": te,
            "signals": signals,
            "payload_preview": traw[:6000],
        }
        if signals:
            signal_terms[vfb_id] = signals

    return {
        "broad_collision_audit": {
            "url": broad_url,
            "http_status": broad_status,
            "error": broad_error,
            "payload_preview": broad_raw[:10000],
        },
        "fanc_db_filtered": filtered,
        "fanc_xref_rows": fanc_rows,
        "fanc_xref_hit_count": len(fanc_rows),
        "fanc_vfb_ids": sorted(fanc_vfb_ids),
        "fanc_term_signal_hits": signal_terms,
        "fanc_terms": terms,
    }


def parse_swc(text: str) -> "np.ndarray":
    import numpy as np
    xyz = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split()
        if len(cols) >= 7:
            xyz.append([float(cols[2]), float(cols[3]), float(cols[4])])
    if not xyz:
        raise ValueError("No SWC nodes parsed")
    return np.asarray(xyz, dtype=float)


def deterministic_sample(points: "np.ndarray", n: int = SAMPLE_POINTS) -> "np.ndarray":
    import numpy as np
    if len(points) <= n:
        return points
    idx = np.linspace(0, len(points) - 1, n, dtype=int)
    return points[idx]


def fanc4_to_3(points: "np.ndarray") -> "np.ndarray":
    import numpy as np
    p = np.asarray(points, dtype=np.uint32)
    status, data, error = post_json(
        f"{FANC_V4_TO_V3_BASE}/values_array",
        {
            "x": [str(v) for v in p[:, 0]],
            "y": [str(v) for v in p[:, 1]],
            "z": [str(v) for v in p[:, 2]],
        },
    )
    if error or status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"fanc4_to_3 failed: status={status} error={error}")
    return np.asarray([data["x"], data["y"], data["z"]], dtype=float).T


def fanc3_to_4(points: "np.ndarray", precision: float = 1.0, max_iterations: int = 20) -> "np.ndarray":
    import numpy as np
    target = np.asarray(points, dtype=float)
    inv = target.copy()
    for i in range(max_iterations):
        mapped = fanc4_to_3(inv)
        errors = mapped - target
        mags = np.sqrt(np.sum(errors * errors, axis=1))
        active = mags > precision
        if not np.any(active):
            break
        rate = 0.5 if i >= 3 else 1.0
        inv[active] = inv[active] - rate * errors[active]
    return inv


def svid_from_pt(points: "np.ndarray") -> list[int]:
    import numpy as np
    p = np.asarray(points, dtype=np.uint32)
    status, data, error = post_json(
        FANC_SVID_LOOKUP,
        {
            "x": [str(v) for v in p[:, 0]],
            "y": [str(v) for v in p[:, 1]],
            "z": [str(v) for v in p[:, 2]],
        },
    )
    if error or status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"svid lookup failed: status={status} error={error}")
    vals = data.get("values", [[]])[0]
    return [int(x) for x in vals]


def direct_chunkedgraph_roots(supervoxels: list[int]) -> tuple[list[int], dict[str, Any]]:
    nonzero = [int(x) for x in supervoxels if int(x) != 0]
    detail: dict[str, Any] = {
        "endpoint_base": FANC_CHUNKEDGRAPH_BASE,
        "table": FANC_CHUNKEDGRAPH_TABLE,
        "method": "direct_read_only_handle_root",
        "http_statuses": {},
    }
    if not nonzero:
        return [], {**detail, "error": "no_nonzero_supervoxels"}

    cache: dict[int, int] = {}
    for svid in dict.fromkeys(nonzero):
        url = (
            f"{FANC_CHUNKEDGRAPH_BASE}/table/{FANC_CHUNKEDGRAPH_TABLE}"
            f"/node/{svid}/root"
        )
        status, raw, error = fetch(url)
        detail["http_statuses"][str(svid)] = status
        if status in (401, 403):
            return [], {**detail, "error": f"auth_required_http_{status}"}
        if error or status != 200 or raw is None:
            return [], {**detail, "error": error or f"HTTP:{status}"}
        try:
            payload = json.loads(raw.decode("utf-8", errors="replace"))
            cache[svid] = int(payload["root_id"])
        except Exception as exc:
            return [], {**detail, "error": f"{type(exc).__name__}:{exc}"}

    return [cache[x] for x in nonzero], {**detail, "error": None}


def cave_roots(supervoxels: list[int]) -> tuple[list[int], dict[str, Any]]:
    direct_roots, direct_detail = direct_chunkedgraph_roots(supervoxels)
    if direct_roots:
        return direct_roots, {
            "datastack": FANC_DATASTACK,
            "resolution_method": "direct_public_chunkedgraph",
            "direct": direct_detail,
            "caveclient": None,
            "error": None,
        }

    detail: dict[str, Any] = {
        "datastack": FANC_DATASTACK,
        "resolution_method": "caveclient_fallback",
        "direct": direct_detail,
    }
    try:
        from caveclient import CAVEclient
        client = CAVEclient(FANC_DATASTACK)
        detail["server_address"] = getattr(client, "server_address", None)
        nonzero = [int(x) for x in supervoxels if int(x) != 0]
        if not nonzero:
            return [], {**detail, "error": "no_nonzero_supervoxels"}
        roots = client.chunkedgraph.get_roots(nonzero)
        return [int(x) for x in roots], {**detail, "error": None}
    except Exception as exc:
        return [], {**detail, "error": f"{type(exc).__name__}:{exc}"}


def summarize_roots(roots: list[int]) -> dict[str, Any]:
    nonzero = [int(x) for x in roots if int(x) != 0]
    counts = Counter(nonzero)
    if not counts:
        return {
            "dominant_root_id": None,
            "dominant_root_count": 0,
            "nonzero_root_count": 0,
            "dominant_fraction": None,
            "root_counts": {},
        }
    root, count = counts.most_common(1)[0]
    return {
        "dominant_root_id": root,
        "dominant_root_count": count,
        "nonzero_root_count": len(nonzero),
        "dominant_fraction": count / len(nonzero),
        "root_counts": {str(k): v for k, v in counts.most_common()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="artifacts/fanc_current_root_audit.json")
    args = ap.parse_args()

    cells: dict[str, Any] = {}
    request_errors = []

    for skid in LEGACY_FANC_SKIDS:
        path = SWC_PATHS[skid]
        url = f"{RAW_BASE}/{quote(path, safe='/')}"
        status, swc, error = fetch_text(url)
        if error or status != 200 or swc is None:
            request_errors.append({"skid": skid, "scope": "author_swc", "status": status, "error": error})
            cells[str(skid)] = {"legacy_namespace": ID_NAMESPACE, "swc_error": error or f"HTTP:{status}"}
            continue

        try:
            import numpy as np
            xyz_nm = parse_swc(swc)
            v3_vox = xyz_nm / np.asarray(VOXEL_NM, dtype=float)
            sample_v3 = deterministic_sample(v3_vox)
            sample_v4 = fanc3_to_4(sample_v3)
            svids = svid_from_pt(sample_v4)
            roots, cave_detail = cave_roots(svids)
            summary = summarize_roots(roots)
            cells[str(skid)] = {
                "legacy_namespace": ID_NAMESPACE,
                "author_swc_path": path,
                "author_swc_http_status": status,
                "swc_node_count": int(len(xyz_nm)),
                "sample_point_count": int(len(sample_v3)),
                "nonzero_supervoxel_count": int(sum(1 for x in svids if x != 0)),
                "unique_supervoxel_count": int(len(set(x for x in svids if x != 0))),
                "cave": cave_detail,
                **summary,
            }
        except Exception as exc:
            request_errors.append({"skid": skid, "scope": "mapping", "error": f"{type(exc).__name__}:{exc}"})
            cells[str(skid)] = {
                "legacy_namespace": ID_NAMESPACE,
                "author_swc_path": path,
                "author_swc_http_status": status,
                "mapping_error": f"{type(exc).__name__}:{exc}",
            }

    vfb_xrefs = {str(skid): vfb_xref_probe(skid) for skid in LEGACY_FANC_SKIDS}

    mapped = [v for v in cells.values() if v.get("dominant_root_id") is not None]
    all_mapped = len(mapped) == len(LEGACY_FANC_SKIDS)
    high_dominance = [
        v for v in mapped
        if v.get("dominant_fraction") is not None and v["dominant_fraction"] >= 0.8
    ]

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "author_source": {
            "repository": AUTHOR_REPO,
            "commit": AUTHOR_COMMIT,
            "legacy_namespace": ID_NAMESPACE,
            "legacy_fanc_skeleton_ids": LEGACY_FANC_SKIDS,
        },
        "official_mapping_path": {
            "v3_to_v4_service": FANC_V4_TO_V3_BASE,
            "supervoxel_service": FANC_SVID_LOOKUP,
            "current_root_service": (
                f"direct {FANC_CHUNKEDGRAPH_BASE}/table/{FANC_CHUNKEDGRAPH_TABLE}/node/<svid>/root "
                f"then CAVEclient({FANC_DATASTACK}).chunkedgraph.get_roots fallback"
            ),
        },
        "cells": cells,
        "vfb_xrefs": vfb_xrefs,
        "known_downstream_target": {
            "malecns_body_id": TARGET_MALECNS_BODY,
            "manc_body_id": TARGET_MANC_BODY,
            "type": TARGET_TYPE,
        },
        "summary": {
            "legacy_fanc_cells_requested": len(LEGACY_FANC_SKIDS),
            "all_sampled_points_resolved_to_supervoxels": all(
                v.get("sample_point_count") is not None
                and v.get("nonzero_supervoxel_count") == v.get("sample_point_count")
                for v in cells.values()
            ),
            "current_root_resolution_auth_blocked_count": sum(
                "AuthException" in str(v.get("cave", {}).get("error", ""))
                for v in cells.values()
            ),
            "current_root_ids_recovered": len(mapped),
            "all_current_root_ids_recovered": all_mapped,
            "high_dominance_root_count": len(high_dominance),
            "legacy_id_equals_other_dataset_id_is_identity_evidence": False,
            "vfb_fanc_xref_hit_count": sum(
                int(rec.get("fanc_xref_hit_count", 0)) for rec in vfb_xrefs.values()
            ),
            "vfb_fanc_terms_with_cross_dataset_signals": sum(
                len(rec.get("fanc_term_signal_hits", {})) for rec in vfb_xrefs.values()
            ),
            "unfiltered_vfb_accession_hits_are_identity_evidence": False,
            "dominant_root_is_curated_cross_dataset_identity": False,
            "curated_fanc_to_manc_snpp_bridge_found": False,
            "exact_polarity_verified": False,
            "automatic_unlock_performed": False,
            "interpretation": (
                "This audit only transports pinned legacy FANC CATMAID skeleton geometry "
                "through the official FANC v3->v4 / supervoxel / chunkedgraph path. A dominant "
                "current FANC root is an ID migration result, not a curated FANC-to-MANC or "
                "R21D12-to-one-cell identity bridge. Decimal ID collisions across namespaces "
                "are explicitly non-evidence."
            ),
        },
        "governance": {
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
        },
        "request_errors": request_errors,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
