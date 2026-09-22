#!/usr/bin/env python3
"""Exact Phelps legacy FANC -> Lee directional-hook supervoxel bridge audit.

This read-only probe asks one narrow question:
Do any author-pinned Phelps/GridTape legacy FANC hook skeletons contain the exact
FANC supervoxel anchor IDs used by Lee et al. to label T1L hook_flexion or
hook_extension cells?

It uses only:
1. pinned Phelps/GridTape author SWCs,
2. the official FANC v3->v4 transform service,
3. the official FANC v4 point->supervoxel service,
4. the pinned Lee FeCO annotation table.

No morphology/NBLAST recomputation is performed. Exact integer supervoxel
intersection is the only positive bridge criterion.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

PHELPS_REPO = "htem/GridTape_VNC_paper"
PHELPS_COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
PHELPS_RAW = f"https://raw.githubusercontent.com/{PHELPS_REPO}/{PHELPS_COMMIT}"

LEE_REPO = "sagrawal/Lee_2024"
LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"
LEE_TABLE_PATH = "synapse_tables/feco_annotation_table.csv"
LEE_RAW = f"https://raw.githubusercontent.com/{LEE_REPO}/{LEE_COMMIT}/{LEE_TABLE_PATH}"

LEGACY_FANC_SKIDS = [25849, 25842, 25856, 24831, 25909]
SWC_PATHS = {
    skid: (
        "neuron_reconstructions/skeletons_in_FANC_space/sensory_neurons/"
        f"left T1 leg nerve hook chordotonal sensory neuron (neuron {skid}).swc"
    )
    for skid in LEGACY_FANC_SKIDS
}

FANC_V4_TO_V3_BASE = (
    "https://catmaid3.hms.harvard.edu/services/transform-service/"
    "dataset/fanc_v4_to_v3/s/2"
)
FANC_SVID_LOOKUP = (
    "https://catmaid3.hms.harvard.edu/services/transform-service/query/"
    "dataset/fanc_v4/s/2/values_array_string_response"
)

VOXEL_NM = (4.3, 4.3, 45.0)
BATCH_SIZE = 96
TIMEOUT = 30
RECEIPT_SCHEMA = "neurofly-fanc-lee-hook-svid-bridge-v0.1"
DECISION_POLICY = "exact_svid_overlap_only_fail_closed"
USER_AGENT = "NeuroFly-fanc-lee-hook-svid-bridge/0.1"

TARGET_TYPE = "SNpp41"
TARGET_MANC_BODY = 97015
TARGET_MALECNS_BODY = 911942

# Hard governance locks remain unless a later review explicitly accepts a gate.
LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


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
    text = raw.decode("utf-8", errors="replace") if raw is not None else None
    return status, text, error


def post_json(url: str, payload: dict[str, Any]) -> tuple[int, Any | None, str | None]:
    status, raw, error = fetch(url, payload=payload)
    if raw is None:
        return status, None, error
    try:
        return status, json.loads(raw.decode("utf-8", errors="replace")), error
    except json.JSONDecodeError:
        return status, {"raw_preview": raw[:1000].decode("utf-8", errors="replace")}, error or "JSONDecodeError"


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


def parse_position(raw: str) -> list[int]:
    vals = re.findall(r"-?\d+", raw or "")
    if len(vals) != 3:
        raise ValueError(f"Could not parse 3D position: {raw!r}")
    return [int(x) for x in vals]


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
    values = data.get("values", [[]])
    if not values or not isinstance(values[0], list):
        raise RuntimeError("svid lookup returned unexpected payload")
    return [int(x) for x in values[0]]


def chunk_rows(points: "np.ndarray", n: int = BATCH_SIZE):
    for start in range(0, len(points), n):
        yield points[start : start + n]


def all_svids_for_legacy_swc(swc_text: str) -> dict[str, Any]:
    import numpy as np

    xyz_nm = parse_swc(swc_text)
    v3_vox = xyz_nm / np.asarray(VOXEL_NM, dtype=float)

    # De-duplicate rounded voxel coordinates before public service calls.
    v3_uint = np.asarray(v3_vox, dtype=np.uint32)
    _, keep = np.unique(v3_uint, axis=0, return_index=True)
    unique_v3 = v3_vox[np.sort(keep)]

    all_svids: list[int] = []
    transformed_points = 0
    for batch in chunk_rows(unique_v3):
        v4 = fanc3_to_4(batch)
        all_svids.extend(svid_from_pt(v4))
        transformed_points += len(batch)

    nonzero = [x for x in all_svids if x != 0]
    return {
        "swc_node_count": int(len(xyz_nm)),
        "unique_v3_voxel_count": int(len(unique_v3)),
        "transformed_point_count": int(transformed_points),
        "nonzero_supervoxel_count": int(len(nonzero)),
        "unique_supervoxel_count": int(len(set(nonzero))),
        "supervoxel_ids": sorted(set(nonzero)),
    }


def parse_lee_hook_rows(text: str) -> list[dict[str, Any]]:
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row.get("valid") != "t":
            continue
        if row.get("classification_system") != "T1L":
            continue
        if row.get("cell_type") not in {"hook_flx", "hook_ext"}:
            continue
        rows.append(
            {
                "annotation_row_index": int(row.get("") or -1),
                "annotation_id": int(row["id"]),
                "cell_type": row["cell_type"],
                "pt_supervoxel_id": int(row["pt_supervoxel_id"]),
                "pt_root_id": int(row["pt_root_id"]),
                "pt_position": parse_position(row["pt_position"]),
            }
        )
    if not rows:
        raise ValueError("No valid T1L hook_flx/hook_ext rows found")
    return rows


def verify_lee_anchors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import numpy as np

    points = np.asarray([r["pt_position"] for r in rows], dtype=np.uint32)
    observed = svid_from_pt(points)
    out = []
    for row, obs in zip(rows, observed):
        item = dict(row)
        item["service_supervoxel_id"] = int(obs)
        item["service_anchor_matches_pinned_svid"] = int(obs) == int(row["pt_supervoxel_id"])
        out.append(item)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request_errors: list[dict[str, Any]] = []

    status, lee_text, lee_error = fetch_text(LEE_RAW)
    if lee_error or status != 200 or lee_text is None:
        raise RuntimeError(f"Lee table fetch failed: status={status} error={lee_error}")

    lee_rows = parse_lee_hook_rows(lee_text)
    verified_lee_rows = verify_lee_anchors(lee_rows)
    verified_anchor_count = sum(1 for r in verified_lee_rows if r["service_anchor_matches_pinned_svid"])

    cells: dict[str, Any] = {}
    for skid in LEGACY_FANC_SKIDS:
        path = SWC_PATHS[skid]
        url = f"{PHELPS_RAW}/{quote(path, safe='/')}"
        status, swc_text, error = fetch_text(url)
        if error or status != 200 or swc_text is None:
            request_errors.append(
                {"skid": skid, "scope": "phelps_swc", "http_status": status, "error": error}
            )
            cells[str(skid)] = {"error": error or f"HTTP:{status}"}
            continue

        try:
            mapped = all_svids_for_legacy_swc(swc_text)
            svid_set = set(mapped.pop("supervoxel_ids"))
            exact_rows = [
                r for r in verified_lee_rows
                if r["service_anchor_matches_pinned_svid"]
                and r["pt_supervoxel_id"] in svid_set
            ]
            directions = sorted({r["cell_type"] for r in exact_rows})
            cells[str(skid)] = {
                "author_swc_path": path,
                **mapped,
                "exact_lee_anchor_overlap_count": len(exact_rows),
                "exact_lee_anchor_overlaps": exact_rows,
                "exact_direction_labels": directions,
                "direction_resolved_by_exact_svid": len(directions) == 1,
                "direction_label": directions[0] if len(directions) == 1 else None,
            }
        except Exception as exc:
            request_errors.append(
                {"skid": skid, "scope": "mapping", "error": f"{type(exc).__name__}:{exc}"}
            )
            cells[str(skid)] = {"author_swc_path": path, "error": f"{type(exc).__name__}:{exc}"}

    resolved = {
        skid: cell.get("direction_label")
        for skid, cell in cells.items()
        if cell.get("direction_resolved_by_exact_svid")
    }
    all_five_resolved = len(resolved) == len(LEGACY_FANC_SKIDS)
    resolved_directions = sorted({v for v in resolved.values() if v is not None})
    all_five_same_direction = all_five_resolved and len(resolved_directions) == 1

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "phelps_source": {
            "repository": PHELPS_REPO,
            "commit": PHELPS_COMMIT,
            "legacy_fanc_catmaid_skeleton_ids": LEGACY_FANC_SKIDS,
        },
        "lee_source": {
            "repository": LEE_REPO,
            "commit": LEE_COMMIT,
            "path": LEE_TABLE_PATH,
            "valid_t1l_hook_row_count": len(lee_rows),
            "service_verified_anchor_count": verified_anchor_count,
            "rows": verified_lee_rows,
        },
        "cells": cells,
        "summary": {
            "legacy_cell_count": len(LEGACY_FANC_SKIDS),
            "legacy_cells_direction_resolved_by_exact_svid": len(resolved),
            "resolved_direction_by_legacy_skid": resolved,
            "all_five_resolved": all_five_resolved,
            "all_five_same_direction": all_five_same_direction,
            "resolved_directions": resolved_directions,
            "exact_svid_overlap_bridge_found": len(resolved) > 0,
            "type_exclusive_directional_candidate_set_found": all_five_same_direction,
            "interpretation": (
                "Only exact equality between a Lee T1L hook anchor supervoxel ID "
                "and a supervoxel traversed by an author-pinned Phelps legacy SWC "
                "counts as a positive bridge. Spatial proximity, same-number IDs, "
                "root inference, and morphology/NBLAST are non-evidence here."
            ),
        },
        "target_context": {
            "systematic_type": TARGET_TYPE,
            "manc_body_id": TARGET_MANC_BODY,
            "malecns_body_id": TARGET_MALECNS_BODY,
            "note": (
                "Merged PR #121 independently freezes SNpp41 -> hook -> "
                "MANC 97015 -> MaleCNS 911942. This probe does not itself "
                "claim a FANC->MANC curated identity."
            ),
        },
        "locks": LOCKS,
        "request_errors": request_errors,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))

    # Infrastructure/data-source failures are hard failures. A clean zero-overlap
    # result is allowed and remains scientifically informative.
    return 1 if request_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
