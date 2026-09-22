#!/usr/bin/env python3
"""Read-only legacy FANC CATMAID -> current FANC root bridge audit.

This probe uses only public resources and never promotes a morphology/coordinate
mapping into a curated FANC->MANC identity. It is designed to answer the
narrow infrastructure question left after PR #120:

Can the five Phelps/GridTape legacy FANC hook CATMAID skeleton IDs be mapped
reproducibly into current FANC4 segmentation identities?

Evidence chain:
1. Pinned author FANC3 SWCs from htem/GridTape_VNC_paper.
2. fancr's published FANC3<->FANC4 transform convention.
3. Public Itanna FANC4 supervoxel lookup.
4. Public FANC ChunkedGraph root endpoint when anonymously readable.
5. VFB search as an independent curated-xref audit.
6. 2023 neck-connective supplement exact-token guard against numeric ID
   collisions across datasets.

The audit is evidence-only and fail-closed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import socket
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


RECEIPT_SCHEMA = "neurofly-fanc-root-bridge-audit-v0.2"
DECISION_POLICY = "evidence_only_no_auto_unlock"
USER_AGENT = "NeuroFly-FANC-root-bridge-audit/0.2"
TIMEOUT = 25

GRIDTAPE_REPO = "htem/GridTape_VNC_paper"
GRIDTAPE_COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
FANCR_REPO = "flyconnectome/fancr"
FANCR_COMMIT = "7b3d429729627d83dad9387f54294272640e87f9"

FANC3_VOXEL_NM = (4.3, 4.3, 45.0)
TRANSFORM_BASE = (
    "https://spine.itanna.io/app/transform-service/dataset/fanc_v4_to_v3"
)
FANC4_SVID_URL = (
    "https://services.itanna.io/app/transform-service/query/dataset/"
    "fanc_v4/s/2/values_array_string_response"
)
FANC_ROOT_BASE = (
    "https://cave.fanc-fly.com/segmentation/api/v1/table/mar2021_prod"
)
VFB_BASE = "https://v3-cached.virtualflybrain.org"

NECK_REPO = "flyconnectome/2023neckconnective"
NECK_COMMIT = "94637d7d82920234ef0bfdbf383c000e74a8b45a"
NECK_FANC_SA_PATH = "Supplemental_files/Supplemental_file10_FANC_SAs.tsv"

KNOWN_MANC_BODY = 97015
KNOWN_MANC_TYPE = "SNpp41"
KNOWN_MALECNS_BODY = 911942

# fancr public test canaries.
CANARY_FANC4_RAW = (34495.0, 82783.0, 1954.0)
CANARY_EXPECTED_SVID = "73186243730767724"
CANARY_EXPECTED_ROOT = "648518346499897667"
CANARY_FANC3_NM = (194569.2, 470101.3, 117630.0)
CANARY_EXPECTED_FANC4_RAW = (45224.0, 109317.0, 2614.0)

TARGETS = {
    25849: {
        "rank": 1,
        "author_nblast_score": 0.508957,
    },
    25842: {
        "rank": 2,
        "author_nblast_score": 0.494256,
    },
    25856: {
        "rank": 3,
        "author_nblast_score": 0.473981,
    },
    24831: {
        "rank": 4,
        "author_nblast_score": 0.468952,
    },
    25909: {
        "rank": 5,
        "author_nblast_score": 0.464603,
    },
}

SWC_PREFIX = (
    "neuron_reconstructions/skeletons_in_FANC_space/sensory_neurons/"
    "left T1 leg nerve hook chordotonal sensory neuron (neuron "
)


def swc_path(skid: int) -> str:
    return f"{SWC_PREFIX}{skid}).swc"


def raw_github(repo: str, commit: str, path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{repo}/{commit}/"
        f"{quote(path, safe='/()')}"
    )


def request(
    url: str,
    *,
    payload: Any | None = None,
    accept: str = "application/json,text/plain,*/*",
) -> tuple[int, bytes | None, str | None]:
    data = None
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            return int(res.status), res.read(), None
    except HTTPError as exc:
        raw = exc.read()
        return int(exc.code), raw, f"HTTPError:{exc.code}"
    except (URLError, TimeoutError, socket.timeout) as exc:
        return 0, None, f"{type(exc).__name__}:{exc}"


def fetch_text(url: str) -> tuple[int, str | None, str | None]:
    status, raw, error = request(url, accept="text/plain,*/*")
    text = raw.decode("utf-8", errors="replace") if raw is not None else None
    return status, text, error


def fetch_json(
    url: str,
    *,
    payload: Any | None = None,
) -> tuple[int, Any | None, str | None]:
    status, raw, error = request(url, payload=payload)
    if raw is None:
        return status, None, error
    text = raw.decode("utf-8", errors="replace")
    try:
        return status, json.loads(text), error
    except json.JSONDecodeError:
        return status, {"raw_preview": text[:4000]}, error or "JSONDecodeError"


def parse_swc(text: str) -> list[tuple[float, float, float]]:
    pts = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 7:
            continue
        try:
            pts.append((float(fields[2]), float(fields[3]), float(fields[4])))
        except ValueError:
            continue
    return pts


def evenly_sample(
    points: list[tuple[float, float, float]],
    n: int = 48,
) -> list[tuple[float, float, float]]:
    if len(points) <= n:
        return points
    if n <= 1:
        return [points[len(points) // 2]]
    idxs = {
        int(round(i * (len(points) - 1) / (n - 1)))
        for i in range(n)
    }
    return [points[i] for i in sorted(idxs)]


def post_transform_map(
    fanc3_nm: list[tuple[float, float, float]],
) -> tuple[int, list[tuple[float, float, float]] | None, str | None, Any]:
    # Mirrors fancr::fanc4to3(..., swap=TRUE):
    # raw3 = nm / voxel; query v4_to_v3 displacement; raw4 = raw3 - delta.
    raw3 = [
        (
            p[0] / FANC3_VOXEL_NM[0],
            p[1] / FANC3_VOXEL_NM[1],
            p[2] / FANC3_VOXEL_NM[2],
        )
        for p in fanc3_nm
    ]
    rounded = [(round(x), round(y), round(z)) for x, y, z in raw3]
    url = f"{TRANSFORM_BASE}/s/2/values_array"
    payload = {
        "x": [int(p[0]) for p in rounded],
        "y": [int(p[1]) for p in rounded],
        "z": [int(p[2]) for p in rounded],
    }
    status, body, error = fetch_json(url, payload=payload)
    if status != 200 or not isinstance(body, dict):
        return status, None, error, body
    dx = body.get("dx")
    dy = body.get("dy")
    if not isinstance(dx, list) or not isinstance(dy, list):
        return status, None, error or "missing_dx_dy", body
    if len(dx) != len(rounded) or len(dy) != len(rounded):
        return status, None, "transform_length_mismatch", body
    out = []
    for p, ddx, ddy in zip(rounded, dx, dy):
        try:
            out.append((float(p[0]) - float(ddx), float(p[1]) - float(ddy), float(p[2])))
        except (TypeError, ValueError):
            out.append((math.nan, math.nan, math.nan))
    return status, out, error, body


def supervoxels(
    fanc4_raw: list[tuple[float, float, float]],
) -> tuple[int, list[str] | None, str | None, Any]:
    valid = [
        p for p in fanc4_raw
        if all(math.isfinite(v) for v in p)
    ]
    payload = {
        "x": [p[0] for p in valid],
        "y": [p[1] for p in valid],
        "z": [p[2] for p in valid],
    }
    status, body, error = fetch_json(FANC4_SVID_URL, payload=payload)
    if status != 200:
        return status, None, error, body
    values: Any = body
    if isinstance(body, dict) and "values" in body:
        values = body["values"]
    while isinstance(values, list) and len(values) == 1 and isinstance(values[0], list):
        values = values[0]
    if not isinstance(values, list):
        return status, None, error or "unexpected_svid_shape", body
    return status, [str(v) for v in values], error, body


def fanc_root(svid: str) -> tuple[int, str | None, str | None, Any]:
    url = f"{FANC_ROOT_BASE}/node/{svid}/root?int64_as_str=1"
    status, body, error = fetch_json(url)
    root = None
    if isinstance(body, (str, int)):
        root = str(body)
    elif isinstance(body, dict):
        for key in ("root_id", "root", "id"):
            if key in body and not isinstance(body[key], (dict, list)):
                root = str(body[key])
                break
    access_redirect = False
    if isinstance(body, dict):
        preview = str(body.get("raw_preview") or "")
        access_redirect = bool(
            re.search(r"accounts\.google\.com|signin|google accounts", preview, re.I)
        )
    if access_redirect:
        root = None
        error = "authentication_required_redirect"
    return status, root, error, {
        "url": url,
        "payload": body,
        "authentication_required_redirect": access_redirect,
    }


def vfb_search(query: str) -> dict[str, Any]:
    url = f"{VFB_BASE}/search?{urlencode({'query': query, 'limit': 100})}"
    status, body, error = fetch_json(url)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True) if body is not None else ""
    roots = sorted(set(re.findall(r"648518346\d{9}", raw)))
    return {
        "url": url,
        "http_status": status,
        "error": error,
        "query": query,
        "has_fanc_context": bool(re.search(r"FANC|Phelps|Maniates|Selvin", raw, re.I)),
        "has_hook_context": bool(re.search(r"hook chordotonal", raw, re.I)),
        "candidate_root_ids_in_payload": roots,
        "preview": raw[:3000],
    }


def exact_token_hits(tsv: str, tokens: set[str]) -> dict[str, list[str]]:
    hits = {t: [] for t in sorted(tokens)}
    for line in tsv.splitlines():
        cols = line.split("\t")
        for token in tokens:
            if token in cols:
                hits[token].append(line[:2000])
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/fanc_root_bridge_audit.json",
    )
    args = parser.parse_args()

    errors: list[dict[str, Any]] = []

    lee_url = raw_github(LEE_REPO, LEE_COMMIT, LEE_FECO_PATH)
    lee_status, lee_text, lee_error = fetch_text(lee_url)
    lee_rows = parse_lee_hook_rows(lee_text or "") if lee_status == 200 else []
    lee_counts = Counter(row["tuning"] for row in lee_rows)
    lee_source_valid = (
        len(lee_rows) == 22
        and dict(lee_counts) == LEE_EXPECTED_COUNTS
        and all(row["pt_supervoxel_id"] and row["pt_root_id"] for row in lee_rows)
    )
    if not lee_source_valid:
        errors.append({
            "scope": "lee_hook_source",
            "status": lee_status,
            "error": lee_error or "unexpected_lee_hook_inventory",
            "counts": dict(lee_counts),
        })

    # Verify all Lee anchor points against the same public FANC4 supervoxel service.
    lee_anchor_svid_status = 0
    lee_anchor_svid_error = None
    lee_anchor_svids: list[str] = []
    if lee_rows:
        lee_anchor_svid_status, anchor_svids, lee_anchor_svid_error, _ = supervoxels(
            [tuple(row["pt_position"]) for row in lee_rows]
        )
        lee_anchor_svids = anchor_svids or []
    lee_anchor_checks = []
    for row, observed in zip(lee_rows, lee_anchor_svids):
        lee_anchor_checks.append({
            **row,
            "observed_supervoxel_id": observed,
            "supervoxel_matches": observed == row["pt_supervoxel_id"],
        })
    lee_anchor_validation_pass = (
        len(lee_anchor_checks) == 22
        and all(row["supervoxel_matches"] for row in lee_anchor_checks)
    )

    # Independent canary 1: published fancr inverse transform example.
    ts, transformed, terr, tbody = post_transform_map([CANARY_FANC3_NM])
    transform_canary = {
        "http_status": ts,
        "error": terr,
        "expected_fanc4_raw": CANARY_EXPECTED_FANC4_RAW,
        "observed_fanc4_raw": transformed[0] if transformed else None,
        "absolute_error_voxels": None,
    }
    if transformed:
        obs = transformed[0]
        errs = [abs(obs[i] - CANARY_EXPECTED_FANC4_RAW[i]) for i in range(3)]
        transform_canary["absolute_error_voxels"] = errs
        transform_canary["pass"] = max(errs) <= 6.0
    else:
        transform_canary["pass"] = False
        errors.append({"scope": "transform_canary", "error": terr, "status": ts})

    # Independent canary 2: published fancr FANC4 raw XYZ -> svid/root example.
    ss, svids, serr, sbody = supervoxels([CANARY_FANC4_RAW])
    observed_svid = svids[0] if svids else None
    svid_canary = {
        "http_status": ss,
        "error": serr,
        "expected_svid": CANARY_EXPECTED_SVID,
        "observed_svid": observed_svid,
        "pass": observed_svid == CANARY_EXPECTED_SVID,
    }
    if ss != 200:
        errors.append({"scope": "svid_canary", "error": serr, "status": ss})

    root_canary_status = 0
    observed_root = None
    root_canary_error = None
    root_canary_payload = None
    if observed_svid:
        root_canary_status, observed_root, root_canary_error, root_canary_payload = fanc_root(
            observed_svid
        )
    root_canary = {
        "http_status": root_canary_status,
        "error": root_canary_error,
        "expected_root": CANARY_EXPECTED_ROOT,
        "observed_root": observed_root,
        "pass": observed_root == CANARY_EXPECTED_ROOT,
        "authentication_or_access_blocked": (
            root_canary_status in {401, 403}
            or root_canary_error == "authentication_required_redirect"
            or bool(
                isinstance(root_canary_payload, dict)
                and root_canary_payload.get("authentication_required_redirect")
            )
        ),
        "request": root_canary_payload,
    }

    # Numeric-collision guard: the neck-connective sensory-ascending table does
    # not provide a cross-dataset bridge for these old Phelps CATMAID IDs.
    neck_url = raw_github(NECK_REPO, NECK_COMMIT, NECK_FANC_SA_PATH)
    ns, neck_text, nerr = fetch_text(neck_url)
    target_tokens = {str(i) for i in TARGETS}
    neck_hits = exact_token_hits(neck_text or "", target_tokens)
    neck_guard = {
        "url": neck_url,
        "http_status": ns,
        "error": nerr,
        "exact_token_hits": neck_hits,
        "all_target_tokens_absent": all(not v for v in neck_hits.values()),
        "interpretation": (
            "Exact numeric equality across FANC CATMAID and MANC/body fields is "
            "not an identity relation. The neck-connective FANC sensory-ascending "
            "supplement is checked only as a collision guard."
        ),
    }

    target_results: dict[str, Any] = {}
    for skid, meta in TARGETS.items():
        path = swc_path(skid)
        url = raw_github(GRIDTAPE_REPO, GRIDTAPE_COMMIT, path)
        fs, swc_text, ferr = fetch_text(url)
        points = parse_swc(swc_text or "")
        sampled = evenly_sample(points, 48)

        tstatus, raw4, txerr, _ = post_transform_map(sampled) if sampled else (0, None, "no_points", None)
        sv_status, target_svids, sv_err, _ = (
            supervoxels(raw4)
            if raw4
            else (0, None, "no_transformed_points", None)
        )
        nonzero = [s for s in (target_svids or []) if s not in {"0", "None", "nan"}]
        svid_counts = Counter(nonzero)
        target_svid_set = set(nonzero)
        lee_exact_overlaps = [
            {
                "tuning": row["tuning"],
                "pt_supervoxel_id": row["pt_supervoxel_id"],
                "pt_root_id": row["pt_root_id"],
                "pt_position": row["pt_position"],
            }
            for row in lee_rows
            if row["pt_supervoxel_id"] in target_svid_set
        ]
        overlap_roots = sorted({row["pt_root_id"] for row in lee_exact_overlaps})
        overlap_tunings = sorted({row["tuning"] for row in lee_exact_overlaps})
        unique_lee_segmentation_bridge = (
            lee_anchor_validation_pass
            and len(overlap_roots) == 1
            and len(overlap_tunings) == 1
        )

        roots: dict[str, dict[str, Any]] = {}
        root_counts: Counter[str] = Counter()
        # Only attempt anonymous root calls if the published root canary succeeds.
        if root_canary["pass"]:
            for svid, count in svid_counts.most_common():
                rs, root, rerr, req = fanc_root(svid)
                roots[svid] = {
                    "node_count": count,
                    "http_status": rs,
                    "root_id": root,
                    "error": rerr,
                    "request_url": req.get("url") if isinstance(req, dict) else None,
                }
                if root:
                    root_counts[root] += count

        dominant_root = root_counts.most_common(1)[0] if root_counts else None
        dominant_root_fraction = (
            dominant_root[1] / sum(root_counts.values())
            if dominant_root and sum(root_counts.values())
            else None
        )

        label = f"left T1 leg nerve hook chordotonal sensory neuron (neuron {skid})"
        vfb = {
            "by_exact_label": vfb_search(label),
            "numeric_id_search_rejected_as_ambiguous": True,
        }

        target_results[str(skid)] = {
            "rank": meta["rank"],
            "author_nblast_score": meta["author_nblast_score"],
            "author_swc": {
                "url": url,
                "http_status": fs,
                "error": ferr,
                "node_count": len(points),
                "sampled_node_count": len(sampled),
            },
            "fanc3_to_fanc4": {
                "http_status": tstatus,
                "error": txerr,
                "transformed_point_count": len(raw4 or []),
            },
            "supervoxels": {
                "http_status": sv_status,
                "error": sv_err,
                "nonzero_count": len(nonzero),
                "unique_nonzero_count": len(svid_counts),
                "top_counts": [
                    {"supervoxel_id": s, "node_count": n}
                    for s, n in svid_counts.most_common(12)
                ],
            },
            "lee_functional_segmentation_bridge": {
                "exact_supervoxel_overlaps": lee_exact_overlaps,
                "overlap_root_ids": overlap_roots,
                "overlap_tunings": overlap_tunings,
                "unique_bridge": unique_lee_segmentation_bridge,
                "mapped_root_id": overlap_roots[0] if unique_lee_segmentation_bridge else None,
                "mapped_tuning": overlap_tunings[0] if unique_lee_segmentation_bridge else None,
            },
            "anonymous_root_lookup": {
                "attempted": bool(root_canary["pass"]),
                "per_supervoxel": roots,
                "root_node_counts": dict(root_counts),
                "dominant_root_id": dominant_root[0] if dominant_root else None,
                "dominant_root_node_count": dominant_root[1] if dominant_root else None,
                "dominant_root_fraction": dominant_root_fraction,
            },
            "vfb": vfb,
        }

        if fs != 200:
            errors.append({"scope": f"swc:{skid}", "status": fs, "error": ferr})
        if tstatus != 200:
            errors.append({"scope": f"transform:{skid}", "status": tstatus, "error": txerr})
        if sv_status != 200:
            errors.append({"scope": f"svid:{skid}", "status": sv_status, "error": sv_err})

    dominant_candidates = {
        skid: rec["anonymous_root_lookup"]["dominant_root_id"]
        for skid, rec in target_results.items()
        if rec["anonymous_root_lookup"]["dominant_root_id"]
    }
    lee_bridge_candidates = {
        skid: {
            "root_id": rec["lee_functional_segmentation_bridge"]["mapped_root_id"],
            "tuning": rec["lee_functional_segmentation_bridge"]["mapped_tuning"],
        }
        for skid, rec in target_results.items()
        if rec["lee_functional_segmentation_bridge"]["unique_bridge"]
    }

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "sources": {
            "gridtape": {
                "repository": GRIDTAPE_REPO,
                "commit": GRIDTAPE_COMMIT,
            },
            "fancr": {
                "repository": FANCR_REPO,
                "commit": FANCR_COMMIT,
                "transform_contract": "R/xform.R::fanc4to3(swap=TRUE)",
                "identity_contract": "R/ids.R::fanc_xyz2id",
            },
            "lee_2024": {
                "repository": LEE_REPO,
                "commit": LEE_COMMIT,
                "path": LEE_FECO_PATH,
                "url": lee_url,
                "http_status": lee_status,
                "hook_count": len(lee_rows),
                "hook_counts_by_tuning": dict(lee_counts),
                "source_valid": lee_source_valid,
                "anchor_supervoxel_http_status": lee_anchor_svid_status,
                "anchor_supervoxel_error": lee_anchor_svid_error,
                "anchor_validation_pass": lee_anchor_validation_pass,
                "anchor_checks": lee_anchor_checks,
            },
            "neck_connective": {
                "repository": NECK_REPO,
                "commit": NECK_COMMIT,
                "path": NECK_FANC_SA_PATH,
            },
        },
        "canaries": {
            "transform": transform_canary,
            "supervoxel": svid_canary,
            "anonymous_root": root_canary,
        },
        "neck_connective_numeric_collision_guard": neck_guard,
        "targets": target_results,
        "known_downstream_target": {
            "malecns_body_id": KNOWN_MALECNS_BODY,
            "manc_body_id": KNOWN_MANC_BODY,
            "type": KNOWN_MANC_TYPE,
        },
        "summary": {
            "transform_canary_pass": bool(transform_canary.get("pass")),
            "supervoxel_canary_pass": bool(svid_canary.get("pass")),
            "anonymous_root_canary_pass": bool(root_canary.get("pass")),
            "anonymous_root_lookup_access_blocked": bool(
                root_canary.get("authentication_or_access_blocked")
            ),
            "legacy_catmaid_to_current_root_candidates": dominant_candidates,
            "all_five_root_candidates_recovered": len(dominant_candidates) == 5,
            "lee_anchor_supervoxel_validation_pass": lee_anchor_validation_pass,
            "legacy_catmaid_to_lee_functional_bridge": lee_bridge_candidates,
            "all_five_lee_functional_bridges_recovered": len(lee_bridge_candidates) == 5,
            "curated_r21d12_to_specific_fanc_em_identity_found": False,
            "curated_fanc_to_manc_snpp_bridge_found": False,
            "exact_polarity_verified": False,
            "interpretation": (
                "An exact overlap between transformed legacy CATMAID skeleton "
                "supervoxels and Lee_2024's validated FeCO anchor supervoxels can "
                "establish a technical old-FANC-to-functional-root bridge without "
                "ChunkedGraph authentication. This still cannot promote the author "
                "NBLAST rank-1 hit into a curated R21D12 identity, and it cannot "
                "establish a curated FANC-to-MANC SNpp41 identity."
            ),
        },
        "governance": {
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
            "automatic_unlock_performed": False,
        },
        "request_errors": errors,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
