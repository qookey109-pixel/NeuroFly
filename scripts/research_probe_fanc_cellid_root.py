#!/usr/bin/env python3
"""Read-only exact FANC cell_ids_v2 cell-id/root audit.

The BANC v1.116 cross-dataset product reports FANC match_id=20201, with
validation=false, and documents match_id semantics as FANC cell_id.
PR #124 independently freezes five exact current FANC hook_flx root IDs.

This probe asks only whether the authoritative FANC cell_ids_v2 table maps
cell_id 20201 to one of those five hook_flx roots. It queries materialization
1116 (the BANC target snapshot) and, when anonymously discoverable, the latest
materialization. It also reverse-queries the five roots.

Authentication failure is infrastructure evidence, not negative scientific
evidence. A positive mapping does not convert validation=false into a curated
BANC↔FANC match and does not unlock polarity/runtime/calibration.
"""

from __future__ import annotations

import argparse
import json
import socket
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CAVE_SERVER = "https://cave.fanc-fly.com"
DATASTACK = "fanc_production_mar2021"
TABLE = "cell_ids_v2"
BANC_FANC_VERSION = 1116
TARGET_FANC_CELL_ID = 20201
HOOK_FLX_ROOTS = {
    648518346481857725,
    648518346509569667,
    648518346494933426,
    648518346514448583,
    648518346494264434,
}
CAVECLIENT_SOURCE_COMMIT = "c57c15f55b6fe9c6dff5e8c6199df57b77b59c2d"
RECEIPT_SCHEMA = "neurofly-fanc-cellid-root-audit-v0.1"
USER_AGENT = "NeuroFly-fanc-cellid-root-audit/0.1"
TIMEOUT = 30

GCS_BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
GCS_PREFIXES = (
    "compiled_data/fanc",
    "fanc/",
)
GCS_HIERARCHY_PREFIX = "compiled_data/fanc_1116/"

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
                or "<base href=\"https://accounts.google.com" in text_l
                or "google accounts" in text_l
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
                "http_status": int(res.status),
                "error": "AUTH_INTERSTITIAL" if auth_interstitial else None,
                "json": parsed,
                "response_is_json": parsed is not None,
                "auth_interstitial": auth_interstitial,
                "final_url": final_url,
                "content_type": content_type,
                "body_preview": text[:3000],
            }
    except HTTPError as exc:
        raw = exc.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        final_url = exc.geturl()
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        auth_interstitial = _looks_like_auth_interstitial(
            final_url, content_type, text
        )
        return {
            "http_status": int(exc.code),
            "error": "AUTH_INTERSTITIAL" if auth_interstitial else f"HTTPError:{exc.code}",
            "json": parsed,
            "response_is_json": parsed is not None,
            "auth_interstitial": auth_interstitial,
            "final_url": final_url,
            "content_type": content_type,
            "body_preview": text[:3000],
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "http_status": 0,
            "error": f"{type(exc).__name__}:{exc}",
            "json": None,
            "response_is_json": False,
            "auth_interstitial": False,
            "final_url": url,
            "content_type": "",
            "body_preview": "",
        }


def list_public_gcs(prefix: str, delimiter: str | None = None) -> dict[str, Any]:
    params = {"prefix": prefix, "max-keys": 1000}
    if delimiter is not None:
        params["delimiter"] = delimiter
    url = (
        f"https://storage.googleapis.com/{GCS_BUCKET}?"
        + urlencode(params)
    )
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            raw = res.read()
            text = raw.decode("utf-8", errors="replace")
            objects: list[dict[str, Any]] = []
            common_prefixes: list[str] = []
            is_truncated = False
            try:
                root = ET.fromstring(text)
                for content in root.iter():
                    if content.tag.endswith("Contents"):
                        key = None
                        size = None
                        for child in content:
                            if child.tag.endswith("Key"):
                                key = child.text
                            elif child.tag.endswith("Size"):
                                try:
                                    size = int(child.text or "0")
                                except ValueError:
                                    size = None
                        if key:
                            objects.append({"name": key, "size": size})
                    elif content.tag.endswith("CommonPrefixes"):
                        for child in content:
                            if child.tag.endswith("Prefix") and child.text:
                                common_prefixes.append(child.text)
                    elif content.tag.endswith("IsTruncated"):
                        is_truncated = (content.text or "").strip().lower() == "true"
            except ET.ParseError:
                objects = []
                common_prefixes = []
            return {
                "url": url,
                "http_status": int(res.status),
                "content_type": res.headers.get("Content-Type", ""),
                "error": None,
                "object_count": len(objects),
                "objects": objects,
                "common_prefixes": sorted(set(common_prefixes)),
                "is_truncated": is_truncated,
                "body_preview": text[:2000],
            }
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return {
            "url": url,
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "error": f"HTTPError:{exc.code}",
            "object_count": 0,
            "objects": [],
            "common_prefixes": [],
            "is_truncated": False,
            "body_preview": text[:2000],
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "url": url,
            "http_status": 0,
            "content_type": "",
            "error": f"{type(exc).__name__}:{exc}",
            "object_count": 0,
            "objects": [],
            "common_prefixes": [],
            "is_truncated": False,
            "body_preview": "",
        }


def versions_url() -> str:
    return f"{CAVE_SERVER}/materialize/api/v3/datastack/{DATASTACK}/versions"


def metadata_url(version: int) -> str:
    return (
        f"{CAVE_SERVER}/materialize/api/v3/datastack/{DATASTACK}/version/"
        f"{version}/table/{TABLE}/metadata"
    )


def query_url(version: int) -> str:
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
        f"{version}/table/{TABLE}/query?{params}"
    )


def discover_versions(value: Any) -> list[int]:
    found: set[int] = set()

    def walk(x: Any) -> None:
        if isinstance(x, bool):
            return
        if isinstance(x, int):
            if x > 0:
                found.add(x)
        elif isinstance(x, str) and x.isdigit():
            found.add(int(x))
        elif isinstance(x, list):
            for item in x:
                walk(item)
        elif isinstance(x, dict):
            for key, item in x.items():
                if key in {"version", "versions", "materialization_version"}:
                    walk(item)

    walk(value)
    return sorted(found)


def collect_mapping_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

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

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            id_value = normalize_int(x.get("id"))
            user_id_value = normalize_int(x.get("user_id"))
            root_value = normalize_int(x.get("pt_root_id"))
            if root_value is not None and (id_value is not None or user_id_value is not None):
                rows.append(
                    {
                        "id": id_value,
                        "user_id": user_id_value,
                        "pt_root_id": root_value,
                        "pt_supervoxel_id": normalize_int(x.get("pt_supervoxel_id")),
                        "pt_position": x.get("pt_position"),
                        "valid": x.get("valid"),
                    }
                )
            for item in x.values():
                walk(item)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(value)
    # stable de-dup
    unique: list[dict[str, Any]] = []
    seen = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def auth_blocked(result: dict[str, Any]) -> bool:
    return (
        result["http_status"] in {401, 403}
        or bool(result.get("auth_interstitial"))
    )


def query_version(version: int) -> dict[str, Any]:
    md = request_json(metadata_url(version))

    by_id_payload = {
        "filter_equal_dict": {TABLE: {"id": TARGET_FANC_CELL_ID}},
        "limit": 20,
    }
    by_id = request_json(query_url(version), by_id_payload)

    by_user_id_payload = {
        "filter_equal_dict": {TABLE: {"user_id": TARGET_FANC_CELL_ID}},
        "limit": 20,
    }
    by_user_id = request_json(query_url(version), by_user_id_payload)

    reverse_payload = {
        "filter_in_dict": {TABLE: {"pt_root_id": sorted(HOOK_FLX_ROOTS)}},
        "limit": 100,
    }
    reverse = request_json(query_url(version), reverse_payload)

    id_rows = collect_mapping_rows(by_id.get("json"))
    user_id_rows = collect_mapping_rows(by_user_id.get("json"))
    reverse_rows = collect_mapping_rows(reverse.get("json"))

    exact_target_rows = [
        r
        for r in [*id_rows, *user_id_rows]
        if (r.get("id") == TARGET_FANC_CELL_ID or r.get("user_id") == TARGET_FANC_CELL_ID)
    ]
    exact_hook_rows = [
        r for r in reverse_rows if r.get("pt_root_id") in HOOK_FLX_ROOTS
    ]
    target_to_hook = [
        r for r in exact_target_rows if r.get("pt_root_id") in HOOK_FLX_ROOTS
    ]
    reverse_target = [
        r
        for r in exact_hook_rows
        if r.get("id") == TARGET_FANC_CELL_ID or r.get("user_id") == TARGET_FANC_CELL_ID
    ]

    return {
        "version": version,
        "metadata_request": md,
        "id_query_request": by_id,
        "user_id_query_request": by_user_id,
        "reverse_root_query_request": reverse,
        "id_mapping_rows": id_rows,
        "user_id_mapping_rows": user_id_rows,
        "reverse_mapping_rows": reverse_rows,
        "exact_target_cell_rows": exact_target_rows,
        "exact_hook_root_rows": exact_hook_rows,
        "target_cell_to_hook_root_rows": target_to_hook,
        "hook_root_to_target_cell_rows": reverse_target,
        "target_cell_to_hook_root_exact_found": bool(target_to_hook),
        "reverse_hook_root_to_target_cell_exact_found": bool(reverse_target),
        "anonymous_auth_blocked": any(
            auth_blocked(x) for x in (md, by_id, by_user_id, reverse)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    gcs_indexes = [list_public_gcs(prefix) for prefix in GCS_PREFIXES]
    gcs_hierarchy = list_public_gcs(GCS_HIERARCHY_PREFIX, delimiter="/")
    gcs_objects = []
    for index in gcs_indexes:
        gcs_objects.extend(index.get("objects", []))
    gcs_objects_by_name = {
        item["name"]: item for item in gcs_objects if item.get("name")
    }
    static_candidates = [
        item
        for item in gcs_objects_by_name.values()
        if any(
            token in item["name"].lower()
            for token in ("meta", "cell_id", "cellid", "annotation")
        )
    ]

    versions_result = request_json(versions_url())
    discovered = discover_versions(versions_result.get("json"))
    latest_version = max(discovered) if discovered else None

    versions_to_query = [BANC_FANC_VERSION]
    if latest_version is not None and latest_version not in versions_to_query:
        versions_to_query.append(latest_version)

    audits = [query_version(v) for v in versions_to_query]
    positive = [
        a
        for a in audits
        if a["target_cell_to_hook_root_exact_found"]
        or a["reverse_hook_root_to_target_cell_exact_found"]
    ]

    transport_errors = []
    all_requests = [versions_result]
    for audit in audits:
        all_requests.extend(
            [
                audit["metadata_request"],
                audit["id_query_request"],
                audit["user_id_query_request"],
                audit["reverse_root_query_request"],
            ]
        )
    for r in all_requests:
        if r["http_status"] == 0:
            transport_errors.append(r["error"])

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "cave_server": CAVE_SERVER,
            "datastack": DATASTACK,
            "table": TABLE,
            "banc_fanc_materialization_version": BANC_FANC_VERSION,
            "caveclient_source_commit": CAVECLIENT_SOURCE_COMMIT,
            "versions_request": versions_result,
            "discovered_versions": discovered,
            "latest_discovered_version": latest_version,
            "public_gcs_bucket": GCS_BUCKET,
            "public_gcs_prefixes": list(GCS_PREFIXES),
            "public_gcs_indexes": gcs_indexes,
            "public_gcs_hierarchy": gcs_hierarchy,
            "public_gcs_static_candidate_objects": static_candidates,
        },
        "targets": {
            "fanc_cell_id": TARGET_FANC_CELL_ID,
            "hook_flx_roots": sorted(HOOK_FLX_ROOTS),
        },
        "version_audits": audits,
        "summary": {
            "versions_queried": versions_to_query,
            "exact_cellid_20201_to_hook_flx_root_found": bool(positive),
            "positive_versions": [a["version"] for a in positive],
            "anonymous_access_auth_blocked": any(
                a["anonymous_auth_blocked"] for a in audits
            ),
            "transport_error_count": len(transport_errors),
            "public_gcs_object_count": len(gcs_objects_by_name),
            "public_gcs_hierarchy_object_count": gcs_hierarchy.get("object_count", 0),
            "public_gcs_hierarchy_common_prefixes": gcs_hierarchy.get("common_prefixes", []),
            "public_gcs_static_candidate_count": len(static_candidates),
            "auth_interstitial_response_count": sum(
                1 for r in all_requests if r.get("auth_interstitial")
            ),
            "non_json_success_response_count": sum(
                1
                for r in all_requests
                if r.get("http_status") == 200 and not r.get("response_is_json")
            ),
            "interpretation": (
                "An exact cell_ids_v2 mapping can strengthen the namespace bridge only. "
                "Because the BANC→FANC NBLAST row has validation=false, even an exact "
                "cell_id 20201→hook_flx root mapping is not a curated FANC→MANC identity "
                "and does not unlock polarity/runtime/calibration."
            ),
        },
        "locks": LOCKS,
        "request_errors": transport_errors,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))

    # 401/403 and HTTP-200 login interstitials are valid fail-closed auth outcomes.
    # Only transport failures hard-fail.
    return 1 if transport_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
