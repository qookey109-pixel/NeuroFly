#!/usr/bin/env python3
"""Audit FANC cell-id/root namespace at v840 and v1116 using official semantics.

This probe combines three pinned author sources:

1. flyconnectome/fancr R/ids.R:
   fanc_segid_from_cellid() and fanc_cellid_from_segid() select the newest
   cell_ids* table and query it with an explicit CAVE materialization version.
2. Dallmann et al. 2025 code:
   FANC datastack fanc_production_mar2021, materialization 840, and
   feco_axons_v0 are used for hook_flx/hook_ext FeCO neurons.
3. Lee 2024 static feco_annotation_table.csv:
   exact pt_supervoxel_id / pt_root_id / hook_flx labels for the five frozen
   Phelps/GridTape hook cells from NeuroFly PR #124.

The audit tests cell_id=20201 against both materialization 840 and 1116, and
reverse-tests the five frozen hook_flx roots. It tries both cell_ids_v2 and
cell_ids table names because fancr deliberately selects the newest cell_ids*
table available.

Authentication/login interstitials are infrastructure boundaries, not negative
scientific evidence. Even a positive 20201->hook_flx namespace mapping does not
turn the BANC NBLAST row (validation=false) into a curated FANC->MANC identity.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CAVE_SERVER = "https://cave.fanc-fly.com"
DATASTACK = "fanc_production_mar2021"
VERSIONS = (840, 1116)
CELL_TABLE_CANDIDATES = ("cell_ids_v2", "cell_ids")
FECO_TABLE = "feco_axons_v0"

FANCR_REPO = "flyconnectome/fancr"
FANCR_COMMIT = "7b3d429729627d83dad9387f54294272640e87f9"
FANCR_IDS_PATH = "R/ids.R"
FANCR_IDS_URL = (
    f"https://raw.githubusercontent.com/{FANCR_REPO}/{FANCR_COMMIT}/"
    f"{FANCR_IDS_PATH}"
)

DALLMANN_REPO = "chrisjdallmann/feco-inhibition"
DALLMANN_COMMIT = "e1233f4a987c532c9f1ab42273af21a0a6a50393"
DALLMANN_NOTEBOOK_PATH = "code/fanc_feco_connectivity.ipynb"
DALLMANN_NOTEBOOK_URL = (
    f"https://raw.githubusercontent.com/{DALLMANN_REPO}/{DALLMANN_COMMIT}/"
    f"{DALLMANN_NOTEBOOK_PATH}"
)

LEE_REPO = "sagrawal/Lee_2024"
LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"
LEE_FECO_PATH = "synapse_tables/feco_annotation_table.csv"
LEE_FECO_URL = (
    f"https://raw.githubusercontent.com/{LEE_REPO}/{LEE_COMMIT}/{LEE_FECO_PATH}"
)

TARGET_FANC_CELL_ID = 20201
HOOK_FLX_ROOTS = {
    648518346481857725,
    648518346509569667,
    648518346494933426,
    648518346514448583,
    648518346494264434,
}
HOOK_FLX_SVIDS = {
    72342438215378040,
    72342438215374178,
    72342438215365972,
    72342438215393919,
    72342438215387174,
}

RECEIPT_SCHEMA = "neurofly-fancr-cellid-version-audit-v0.1"
USER_AGENT = "NeuroFly-fancr-cellid-version-audit/0.1"
TIMEOUT = 35

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=TIMEOUT) as res:
        return res.read().decode("utf-8", errors="replace")


def _looks_like_auth_interstitial(final_url: str, content_type: str, text: str) -> bool:
    u = final_url.lower()
    c = content_type.lower()
    t = text[:12000].lower()
    return (
        "accounts.google.com" in u
        or (
            "text/html" in c
            and (
                "accounts.google.com" in t
                or "google accounts" in t
                or "<base href=\"https://accounts.google.com" in t
            )
        )
    )


def request_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            raw = res.read()
            text = raw.decode("utf-8", errors="replace")
            final_url = res.geturl()
            content_type = res.headers.get("Content-Type", "")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            auth = _looks_like_auth_interstitial(final_url, content_type, text)
            return {
                "http_status": int(res.status),
                "final_url": final_url,
                "content_type": content_type,
                "response_is_json": parsed is not None,
                "auth_interstitial": auth,
                "error": "AUTH_INTERSTITIAL" if auth else None,
                "json": parsed,
                "body_preview": text[:1800],
            }
    except HTTPError as exc:
        raw = exc.read()
        text = raw.decode("utf-8", errors="replace")
        final_url = exc.geturl()
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        auth = _looks_like_auth_interstitial(final_url, content_type, text)
        return {
            "http_status": int(exc.code),
            "final_url": final_url,
            "content_type": content_type,
            "response_is_json": parsed is not None,
            "auth_interstitial": auth,
            "error": "AUTH_INTERSTITIAL" if auth else f"HTTPError:{exc.code}",
            "json": parsed,
            "body_preview": text[:1800],
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "http_status": 0,
            "final_url": url,
            "content_type": "",
            "response_is_json": False,
            "auth_interstitial": False,
            "error": f"{type(exc).__name__}:{exc}",
            "json": None,
            "body_preview": "",
        }


def query_url(version: int, table: str) -> str:
    params = urlencode(
        {
            "return_pyarrow": "false",
            "arrow_format": "false",
            "split_positions": "false",
            "direct_sql_pandas": "true",
        }
    )
    return (
        f"{CAVE_SERVER}/materialize/api/v3/datastack/{DATASTACK}/version/"
        f"{version}/table/{table}/query?{params}"
    )


def normalize_int(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit():
            return int(s)
    return None


def collect_rows(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            keys = set(x)
            if keys.intersection({"id", "pt_root_id", "cell_type", "pt_supervoxel_id"}):
                out.append(dict(x))
            for item in x.values():
                walk(item)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(value)
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in out:
        k = json.dumps(row, sort_keys=True, default=str)
        if k not in seen:
            seen.add(k)
            unique.append(row)
    return unique


def verify_fancr_source(text: str) -> dict[str, Any]:
    checks = {
        "fanc_cellid_from_segid_defined": "fanc_cellid_from_segid <- function" in text,
        "fanc_segid_from_cellid_defined": "fanc_segid_from_cellid <- function" in text,
        "explicit_version_forwarded": "version=version" in text,
        "filter_by_pt_root_id": "idlist=list(pt_root_id=rootids)" in text,
        "filter_by_cell_id": "idlist=list(id=cellids)" in text,
        "newest_cell_ids_table_selected": 'grep("cell_ids", tablenames' in text,
    }
    return {
        "checks": checks,
        "all_verified": all(checks.values()),
    }


def verify_dallmann_source(text: str) -> dict[str, Any]:
    checks = {
        "fanc_datastack": "fanc_production_mar2021" in text,
        "materialization_840": "client.materialize.version = 840" in text,
        "feco_table": "feco_axons_v0" in text,
        "hook_flx": "hook_flx" in text,
        "hook_ext": "hook_ext" in text,
        "pt_root_id": "pt_root_id" in text,
    }
    return {
        "checks": checks,
        "all_verified": all(checks.values()),
    }


def verify_lee_static(text: str) -> dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO(text)))
    selected = []
    for row in rows:
        root = normalize_int(row.get("pt_root_id"))
        svid = normalize_int(row.get("pt_supervoxel_id"))
        if root in HOOK_FLX_ROOTS:
            selected.append(
                {
                    "id": normalize_int(row.get("id")),
                    "classification_system": row.get("classification_system"),
                    "cell_type": row.get("cell_type"),
                    "pt_supervoxel_id": svid,
                    "pt_root_id": root,
                    "pt_position": row.get("pt_position"),
                }
            )
    exact = (
        len(selected) == 5
        and {r["pt_root_id"] for r in selected} == HOOK_FLX_ROOTS
        and {r["pt_supervoxel_id"] for r in selected} == HOOK_FLX_SVIDS
        and all(r["classification_system"] == "T1L" for r in selected)
        and all(r["cell_type"] == "hook_flx" for r in selected)
    )
    return {
        "row_count": len(rows),
        "target_rows": sorted(selected, key=lambda r: r["id"] or 0),
        "five_exact_hook_flx_rows_verified": exact,
    }


def audit_cell_table(version: int, table: str) -> dict[str, Any]:
    forward = request_json(
        query_url(version, table),
        {
            "filter_equal_dict": {table: {"id": TARGET_FANC_CELL_ID}},
            "limit": 20,
        },
    )
    reverse = request_json(
        query_url(version, table),
        {
            "filter_in_dict": {table: {"pt_root_id": sorted(HOOK_FLX_ROOTS)}},
            "limit": 100,
        },
    )
    frows = collect_rows(forward.get("json"))
    rrows = collect_rows(reverse.get("json"))

    forward_hits = []
    for row in frows:
        rid = normalize_int(row.get("pt_root_id"))
        cid = normalize_int(row.get("id"))
        if cid == TARGET_FANC_CELL_ID:
            forward_hits.append({"id": cid, "pt_root_id": rid})

    reverse_hits = []
    for row in rrows:
        rid = normalize_int(row.get("pt_root_id"))
        cid = normalize_int(row.get("id"))
        if rid in HOOK_FLX_ROOTS:
            reverse_hits.append({"id": cid, "pt_root_id": rid})

    exact = [
        row for row in forward_hits
        if row["pt_root_id"] in HOOK_FLX_ROOTS
    ]
    reverse_exact = [
        row for row in reverse_hits
        if row["id"] == TARGET_FANC_CELL_ID
    ]

    return {
        "version": version,
        "table": table,
        "forward_request": forward,
        "reverse_request": reverse,
        "forward_rows": forward_hits,
        "reverse_rows": reverse_hits,
        "exact_20201_to_hook_flx_root_found": bool(exact or reverse_exact),
        "exact_rows": exact or reverse_exact,
        "auth_blocked": bool(
            forward.get("auth_interstitial")
            or reverse.get("auth_interstitial")
            or forward.get("http_status") in {401, 403}
            or reverse.get("http_status") in {401, 403}
        ),
    }


def audit_feco_v840() -> dict[str, Any]:
    result = request_json(
        query_url(840, FECO_TABLE),
        {
            "filter_in_dict": {FECO_TABLE: {"pt_root_id": sorted(HOOK_FLX_ROOTS)}},
            "limit": 100,
        },
    )
    rows = []
    for row in collect_rows(result.get("json")):
        rid = normalize_int(row.get("pt_root_id"))
        if rid in HOOK_FLX_ROOTS:
            rows.append(
                {
                    "id": normalize_int(row.get("id")),
                    "classification_system": row.get("classification_system"),
                    "cell_type": row.get("cell_type"),
                    "pt_supervoxel_id": normalize_int(row.get("pt_supervoxel_id")),
                    "pt_root_id": rid,
                }
            )
    return {
        "request": result,
        "rows": rows,
        "five_hook_flx_rows_found": (
            len({r["pt_root_id"] for r in rows}) == 5
            and all(r.get("cell_type") == "hook_flx" for r in rows)
        ),
        "auth_blocked": bool(
            result.get("auth_interstitial") or result.get("http_status") in {401, 403}
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    errors: list[dict[str, str]] = []

    try:
        fancr_text = fetch_text(FANCR_IDS_URL)
        fancr = verify_fancr_source(fancr_text)
    except Exception as exc:
        fancr = {"all_verified": False, "error": repr(exc)}
        errors.append({"scope": "fancr_source", "error": repr(exc)})

    try:
        dallmann_text = fetch_text(DALLMANN_NOTEBOOK_URL)
        dallmann = verify_dallmann_source(dallmann_text)
    except Exception as exc:
        dallmann = {"all_verified": False, "error": repr(exc)}
        errors.append({"scope": "dallmann_source", "error": repr(exc)})

    try:
        lee_text = fetch_text(LEE_FECO_URL)
        lee = verify_lee_static(lee_text)
    except Exception as exc:
        lee = {"five_exact_hook_flx_rows_verified": False, "error": repr(exc)}
        errors.append({"scope": "lee_static", "error": repr(exc)})

    cell_audits = [
        audit_cell_table(version, table)
        for version in VERSIONS
        for table in CELL_TABLE_CANDIDATES
    ]
    feco_840 = audit_feco_v840()

    positive = [
        a for a in cell_audits if a["exact_20201_to_hook_flx_root_found"]
    ]
    auth_count = sum(
        1
        for a in cell_audits
        for req_name in ("forward_request", "reverse_request")
        if a[req_name].get("auth_interstitial")
    )
    if feco_840["request"].get("auth_interstitial"):
        auth_count += 1

    transport_errors = []
    for audit in cell_audits:
        for req_name in ("forward_request", "reverse_request"):
            req = audit[req_name]
            if req.get("http_status") == 0:
                transport_errors.append(req.get("error"))
    if feco_840["request"].get("http_status") == 0:
        transport_errors.append(feco_840["request"].get("error"))

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "fancr": {
                "repository": FANCR_REPO,
                "commit": FANCR_COMMIT,
                "path": FANCR_IDS_PATH,
                "verification": fancr,
            },
            "dallmann_2025": {
                "repository": DALLMANN_REPO,
                "commit": DALLMANN_COMMIT,
                "path": DALLMANN_NOTEBOOK_PATH,
                "verification": dallmann,
            },
            "lee_2024": {
                "repository": LEE_REPO,
                "commit": LEE_COMMIT,
                "path": LEE_FECO_PATH,
                "verification": lee,
            },
        },
        "targets": {
            "fanc_cell_id": TARGET_FANC_CELL_ID,
            "hook_flx_roots": sorted(HOOK_FLX_ROOTS),
            "hook_flx_supervoxels": sorted(HOOK_FLX_SVIDS),
            "versions": list(VERSIONS),
            "cell_table_candidates": list(CELL_TABLE_CANDIDATES),
        },
        "cell_id_audits": cell_audits,
        "feco_v840_audit": feco_840,
        "summary": {
            "official_fancr_semantics_verified": bool(fancr.get("all_verified")),
            "dallmann_v840_feco_source_verified": bool(dallmann.get("all_verified")),
            "lee_static_five_hook_flx_rows_verified": bool(
                lee.get("five_exact_hook_flx_rows_verified")
            ),
            "exact_cellid_20201_to_hook_flx_root_found": bool(positive),
            "positive_version_tables": [
                {"version": a["version"], "table": a["table"], "rows": a["exact_rows"]}
                for a in positive
            ],
            "auth_interstitial_request_count": auth_count,
            "transport_error_count": len(transport_errors),
            "interpretation": (
                "This audit resolves only the FANC namespace question. A positive "
                "cell_id=20201 to hook_flx root mapping does not validate the BANC "
                "NBLAST match, whose published validation flag remains false. No "
                "curated FANC-to-MANC identity or polarity/runtime authorization is "
                "created automatically."
            ),
        },
        "locks": LOCKS,
        "request_errors": errors + [
            {"scope": "transport", "error": e}
            for e in transport_errors
            if e
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))

    return 1 if errors or transport_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
