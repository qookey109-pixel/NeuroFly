#!/usr/bin/env python3
"""Audit the official CAVE global->local route for frozen FANC FeCO targets.

Previous NeuroFly audit #126 queried the historical/annotation-facing
cave.fanc-fly.com hostname and correctly classified its Google OAuth interstitial.
CAVEclient itself defaults to global.daf-apis.com, asks the InfoService for a
datastack's local_server, and then constructs MaterializationEngine URLs from
that server.

This probe follows that official route without credentials.

Questions:
1) At materialization 840, does feco_axons_v0 return the five PR #124 roots and
   label them hook_flx?
2) At materialization 1116, does cell_ids_v2 map exact id=20201 to one of those
   five roots?

Even if (2) is positive, the BANC->FANC NBLAST row remains validation=false.
That would resolve a namespace mapping, not a curated FANC->MANC identity.
"""

from __future__ import annotations

import argparse
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GLOBAL_SERVER = "https://global.daf-apis.com"
DATASTACK = "fanc_production_mar2021"
GLOBAL_INFO_URL = (
    f"{GLOBAL_SERVER}/info/api/v2/datastack/full/{DATASTACK}"
)

FECO_TABLE = "feco_axons_v0"
FECO_VERSION = 840
CELL_ID_TABLE = "cell_ids_v2"
CELL_ID_VERSION = 1116
TARGET_FANC_CELL_ID = 20201

HOOK_FLX_ROOTS = {
    648518346481857725,
    648518346509569667,
    648518346494933426,
    648518346514448583,
    648518346494264434,
}

EXPECTED_STATIC_HOOK_ROWS = {
    648518346481857725: 72342438215378040,
    648518346509569667: 72342438215374178,
    648518346494933426: 72342438215365972,
    648518346514448583: 72342438215393919,
    648518346494264434: 72342438215387174,
}

CAVECLIENT_SOURCE_COMMIT = "c57c15f55b6fe9c6dff5e8c6199df57b77b59c2d"
BANCPIPELINE_SOURCE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"
LEE_SOURCE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"
RECEIPT_SCHEMA = "neurofly-fanc-cave-global-route-audit-v0.1"
USER_AGENT = "NeuroFly-fanc-cave-global-route-audit/0.1"
TIMEOUT = 30

FANC_SEGMENT_PROPERTIES_URL = (
    "https://storage.googleapis.com/"
    "lee-lab_brain-and-nerve-cord-fly-connectome/"
    "imported_meshes/fanc_1116_meshes_elastix_tpsreg_240721/"
    "segment_properties/info"
)

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


def _looks_like_auth_interstitial(final_url: str, content_type: str, text: str) -> bool:
    final_url_l = final_url.lower()
    content_type_l = content_type.lower()
    text_l = text[:12000].lower()
    return (
        "accounts.google.com" in final_url_l
        or (
            "text/html" in content_type_l
            and (
                "accounts.google.com" in text_l
                or "google accounts" in text_l
                or "sign in" in text_l
            )
        )
    )


def request_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        url,
        data=body,
        method="POST" if payload is not None else "GET",
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
            auth_interstitial = _looks_like_auth_interstitial(
                final_url, content_type, text
            )
            return {
                "url": url,
                "http_status": int(res.status),
                "error": "AUTH_INTERSTITIAL" if auth_interstitial else None,
                "json": parsed,
                "response_is_json": parsed is not None,
                "auth_interstitial": auth_interstitial,
                "final_url": final_url,
                "content_type": content_type,
                "body_preview": text[:4000],
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
        auth_interstitial = _looks_like_auth_interstitial(
            final_url, content_type, text
        )
        return {
            "url": url,
            "http_status": int(exc.code),
            "error": "AUTH_INTERSTITIAL" if auth_interstitial else f"HTTPError:{exc.code}",
            "json": parsed,
            "response_is_json": parsed is not None,
            "auth_interstitial": auth_interstitial,
            "final_url": final_url,
            "content_type": content_type,
            "body_preview": text[:4000],
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "url": url,
            "http_status": 0,
            "error": f"{type(exc).__name__}:{exc}",
            "json": None,
            "response_is_json": False,
            "auth_interstitial": False,
            "final_url": url,
            "content_type": "",
            "body_preview": "",
        }


def find_key_values(value: Any, key_name: str) -> list[Any]:
    found: list[Any] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for key, item in x.items():
                if key == key_name:
                    found.append(item)
                walk(item)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(value)
    return found


def normalize_server(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().rstrip("/")
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return None


def query_url(server: str, version: int, table: str) -> str:
    params = urlencode(
        {
            "return_pyarrow": "false",
            "arrow_format": "false",
            "split_positions": "false",
            "direct_sql_pandas": "true",
        }
    )
    return (
        f"{server}/materialize/api/v3/datastack/{DATASTACK}/version/"
        f"{version}/table/{table}/query?{params}"
    )


def metadata_url(server: str, version: int, table: str) -> str:
    return (
        f"{server}/materialize/api/v3/datastack/{DATASTACK}/version/"
        f"{version}/table/{table}/metadata"
    )


def versions_url(server: str) -> str:
    return f"{server}/materialize/api/v3/datastack/{DATASTACK}/versions"


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
    rows: list[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            if any(
                key in x
                for key in (
                    "pt_root_id",
                    "pt_supervoxel_id",
                    "cell_type",
                    "classification_system",
                    "id",
                )
            ):
                rows.append(dict(x))
            for item in x.values():
                walk(item)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(value)
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        marker = json.dumps(row, sort_keys=True, default=str)
        if marker not in seen:
            seen.add(marker)
            unique.append(row)
    return unique


def audit_public_segment_properties() -> dict[str, Any]:
    response = request_json(FANC_SEGMENT_PROPERTIES_URL)
    parsed = response.get("json")
    result = {
        "request": response,
        "cell_id": TARGET_FANC_CELL_ID,
        "found": False,
        "label": None,
        "tags": [],
        "property_schema": [],
    }
    if not isinstance(parsed, dict):
        return result

    inline = parsed.get("inline")
    if not isinstance(inline, dict):
        return result

    ids = inline.get("ids")
    properties = inline.get("properties")
    if not isinstance(ids, list) or not isinstance(properties, list):
        return result

    result["property_schema"] = [
        {
            "id": prop.get("id"),
            "type": prop.get("type"),
        }
        for prop in properties
        if isinstance(prop, dict)
    ]

    target = str(TARGET_FANC_CELL_ID)
    try:
        idx = [str(x) for x in ids].index(target)
    except ValueError:
        return result

    result["found"] = True
    for prop in properties:
        if not isinstance(prop, dict):
            continue
        prop_id = prop.get("id")
        values = prop.get("values")
        if not isinstance(values, list) or idx >= len(values):
            continue
        if prop_id == "label":
            result["label"] = values[idx]
        elif prop_id == "tags":
            global_tags = prop.get("tags")
            tag_ids = values[idx]
            if isinstance(global_tags, list) and isinstance(tag_ids, list):
                decoded = []
                for tag_id in tag_ids:
                    tag_index = normalize_int(tag_id)
                    if tag_index is not None and 0 <= tag_index < len(global_tags):
                        decoded.append(global_tags[tag_index])
                result["tags"] = decoded

    return result


def audit_server(server: str) -> dict[str, Any]:
    versions = request_json(versions_url(server))

    feco_metadata = request_json(metadata_url(server, FECO_VERSION, FECO_TABLE))
    feco_query = request_json(
        query_url(server, FECO_VERSION, FECO_TABLE),
        {
            "filter_in_dict": {
                FECO_TABLE: {"pt_root_id": sorted(HOOK_FLX_ROOTS)}
            },
            "limit": 100,
        },
    )
    feco_rows = collect_rows(feco_query.get("json"))
    exact_feco_rows = [
        row for row in feco_rows
        if normalize_int(row.get("pt_root_id")) in HOOK_FLX_ROOTS
    ]
    exact_feco_hook_flx_rows = [
        row for row in exact_feco_rows
        if str(row.get("cell_type", "")).strip() == "hook_flx"
    ]

    cell_metadata = request_json(
        metadata_url(server, CELL_ID_VERSION, CELL_ID_TABLE)
    )
    cell_by_id = request_json(
        query_url(server, CELL_ID_VERSION, CELL_ID_TABLE),
        {
            "filter_equal_dict": {
                CELL_ID_TABLE: {"id": TARGET_FANC_CELL_ID}
            },
            "limit": 20,
        },
    )
    cell_by_roots = request_json(
        query_url(server, CELL_ID_VERSION, CELL_ID_TABLE),
        {
            "filter_in_dict": {
                CELL_ID_TABLE: {"pt_root_id": sorted(HOOK_FLX_ROOTS)}
            },
            "limit": 100,
        },
    )

    cell_rows = collect_rows(cell_by_id.get("json"))
    reverse_rows = collect_rows(cell_by_roots.get("json"))

    target_cell_rows = [
        row for row in cell_rows
        if normalize_int(row.get("id")) == TARGET_FANC_CELL_ID
    ]
    target_cell_to_hook_rows = [
        row for row in target_cell_rows
        if normalize_int(row.get("pt_root_id")) in HOOK_FLX_ROOTS
    ]
    reverse_hook_to_20201_rows = [
        row for row in reverse_rows
        if (
            normalize_int(row.get("id")) == TARGET_FANC_CELL_ID
            and normalize_int(row.get("pt_root_id")) in HOOK_FLX_ROOTS
        )
    ]

    requests = [
        versions,
        feco_metadata,
        feco_query,
        cell_metadata,
        cell_by_id,
        cell_by_roots,
    ]

    return {
        "server": server,
        "versions_request": versions,
        "feco_v840": {
            "metadata_request": feco_metadata,
            "query_request": feco_query,
            "exact_target_rows": exact_feco_rows,
            "exact_hook_flx_rows": exact_feco_hook_flx_rows,
            "all_five_roots_returned": {
                normalize_int(row.get("pt_root_id"))
                for row in exact_feco_rows
            } == HOOK_FLX_ROOTS,
            "all_returned_targets_are_hook_flx": (
                len(exact_feco_rows) == 5
                and len(exact_feco_hook_flx_rows) == 5
            ),
        },
        "cell_ids_v2_v1116": {
            "metadata_request": cell_metadata,
            "id_query_request": cell_by_id,
            "reverse_root_query_request": cell_by_roots,
            "target_cell_rows": target_cell_rows,
            "target_cell_to_hook_rows": target_cell_to_hook_rows,
            "reverse_hook_to_20201_rows": reverse_hook_to_20201_rows,
            "exact_20201_to_hook_root_found": bool(
                target_cell_to_hook_rows or reverse_hook_to_20201_rows
            ),
        },
        "anonymous_auth_blocked": any(
            r.get("http_status") in {401, 403}
            or bool(r.get("auth_interstitial"))
            for r in requests
        ),
        "transport_error_count": sum(
            1 for r in requests if r.get("http_status") == 0
        ),
        "json_response_count": sum(
            1 for r in requests if r.get("response_is_json")
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    info = request_json(GLOBAL_INFO_URL)
    local_server_values = find_key_values(info.get("json"), "local_server")
    local_servers = [
        server
        for server in (
            normalize_server(value) for value in local_server_values
        )
        if server is not None
    ]

    server_candidates: list[str] = []
    for server in [*local_servers, GLOBAL_SERVER]:
        if server not in server_candidates:
            server_candidates.append(server)

    audits = [audit_server(server) for server in server_candidates]
    public_segment_properties = audit_public_segment_properties()

    feco_positive = [
        audit for audit in audits
        if audit["feco_v840"]["all_five_roots_returned"]
        and audit["feco_v840"]["all_returned_targets_are_hook_flx"]
    ]
    cellid_positive = [
        audit for audit in audits
        if audit["cell_ids_v2_v1116"]["exact_20201_to_hook_root_found"]
    ]

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "global_server": GLOBAL_SERVER,
            "global_info_url": GLOBAL_INFO_URL,
            "global_info_request": info,
            "discovered_local_servers": local_servers,
            "server_candidates": server_candidates,
            "caveclient_source_commit": CAVECLIENT_SOURCE_COMMIT,
            "bancpipeline_source_commit": BANCPIPELINE_SOURCE_COMMIT,
            "lee_source_commit": LEE_SOURCE_COMMIT,
        },
        "targets": {
            "feco_table": FECO_TABLE,
            "feco_version": FECO_VERSION,
            "cell_id_table": CELL_ID_TABLE,
            "cell_id_version": CELL_ID_VERSION,
            "fanc_cell_id": TARGET_FANC_CELL_ID,
            "hook_flx_roots": sorted(HOOK_FLX_ROOTS),
            "expected_static_root_supervoxels": {
                str(root): svid
                for root, svid in sorted(EXPECTED_STATIC_HOOK_ROWS.items())
            },
        },
        "server_audits": audits,
        "public_segment_properties": public_segment_properties,
        "summary": {
            "global_info_json_received": bool(info.get("response_is_json")),
            "global_info_auth_blocked": bool(info.get("auth_interstitial"))
            or info.get("http_status") in {401, 403},
            "local_server_discovered": bool(local_servers),
            "official_feco_v840_all_five_hook_flx_confirmed": bool(feco_positive),
            "cell_id_20201_to_hook_flx_root_found": bool(cellid_positive),
            "public_segment_properties_20201_found": bool(
                public_segment_properties.get("found")
            ),
            "public_segment_properties_20201_label": (
                public_segment_properties.get("label")
            ),
            "public_segment_properties_20201_tags": (
                public_segment_properties.get("tags")
            ),
            "feco_positive_servers": [a["server"] for a in feco_positive],
            "cellid_positive_servers": [a["server"] for a in cellid_positive],
            "interpretation": (
                "A positive feco_axons_v0 result independently confirms the exact "
                "directional FANC root labels through the official CAVE route. A "
                "positive cell_ids_v2 result resolves cell_id=20201 to a FANC root. "
                "Neither converts BANC validation=false into a curated FANC->MANC "
                "identity, so governance locks remain false."
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

    # Network/auth outcomes are evidence and remain fail-closed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
