#!/usr/bin/env python3
"""Read-only VFBquery audit for a curated FeCO hook polarity bridge.

The audit is intentionally cache-first and failure-tolerant:
- one slow VFB endpoint must not discard the rest of the evidence receipt;
- exact MaleCNS -> MANC fields are extracted when exposed;
- directional SNpp evidence must occur inside an SNpp term payload, not merely
  somewhere else in the combined receipt.

It never unlocks NeuroFly polarity/calibration/runtime automatically.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "https://v3-cached.virtualflybrain.org"
USER_AGENT = "NeuroFly-VFB-curated-identity-audit/0.2"
DECISION_POLICY = "evidence_only_no_auto_unlock"
REQUEST_TIMEOUT_SECONDS = 20

FANC_R21D12_TERM = "VFB_001028lx"
FANC_R21D12_NATIVE = "570810"

KNOWN_MALECNS_TERMS = {
    "SNpp39": {
        "810041": "VFB_jrmc1720",
        "833439": "VFB_jrmc171l",
        "903843": "VFB_jrmc171p",
        "913886": "VFB_jrmc1724",
    },
    "SNpp41": {
        "813147": "VFB_jrmc1738",
        "819524": "VFB_jrmc1739",
        "819559": "VFB_jrmc173g",
        "911942": "VFB_jrmc173f",
    },
}

SEARCH_QUERIES = ["SNpp39", "SNpp41", "R21D12", "570810"]

KEY_PATTERNS = {
    "snpp39": re.compile(r"SNpp39", re.I),
    "snpp41": re.compile(r"SNpp41", re.I),
    "r21d12": re.compile(r"R21D12|GMR21D12", re.I),
    "fanc570810": re.compile(r"570810|VFB_001028lx", re.I),
    "malecns": re.compile(r"MaleCNS|male-cns", re.I),
    "manc": re.compile(r"\bMANC\b|manc:", re.I),
    "prothoracic": re.compile(r"prothoracic|ProLN|T1", re.I),
    "mesothoracic": re.compile(r"mesothoracic|MesoLN|T2", re.I),
    "metathoracic": re.compile(r"metathoracic|MetaLN|T3", re.I),
    "hook": re.compile(r"hook", re.I),
    "flexion": re.compile(r"flexion", re.I),
    "extension": re.compile(r"extension", re.I),
}

MANC_FIELD_NAMES = {
    "mancBodyid",
    "mancBodyId",
    "manc_bodyid",
    "manc_body_id",
    "mancGroup",
    "manc_group",
    "mancType",
    "manc_type",
}


def fetch_json(
    path: str,
    params: dict[str, Any] | None = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> tuple[int, Any | None, str, str | None]:
    query = ("?" + urlencode(params, doseq=True)) if params else ""
    url = f"{BASE}{path}{query}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            return int(res.status), json.loads(raw), url, None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:5000]}
        return int(exc.code), payload, url, f"HTTPError:{exc.code}"
    except (URLError, TimeoutError, socket.timeout) as exc:
        return 0, None, url, f"{type(exc).__name__}:{exc}"


def compact_hits(payload: Any, *, max_records: int = 80) -> list[dict[str, Any]]:
    """Collect compact JSON subtrees containing a relevant token."""
    out: list[dict[str, Any]] = []

    def walk(obj: Any, path: str) -> None:
        if len(out) >= max_records:
            return
        if isinstance(obj, dict):
            raw = json.dumps(obj, sort_keys=True, ensure_ascii=False)
            matched = [name for name, pat in KEY_PATTERNS.items() if pat.search(raw)]
            if matched:
                summary: dict[str, Any] = {"path": path or "$", "matched": matched}
                for key in (
                    "id", "short_form", "label", "name", "symbol", "accession",
                    "dataset", "type", "class", "subclass", "synonyms",
                    "mancBodyid", "mancBodyId", "manc_bodyid", "manc_body_id",
                    "mancGroup", "manc_group", "mancType", "manc_type",
                    "description", "title",
                ):
                    if key in obj and not isinstance(obj[key], (dict, list)):
                        summary[key] = obj[key]
                if len(summary) <= 2:
                    summary["preview"] = raw[:900]
                out.append(summary)
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    walk(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                if isinstance(value, (dict, list)):
                    walk(value, f"{path}[{idx}]")

    walk(payload, "")
    return out


def payload_flags(payload: Any) -> dict[str, bool]:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return {name: bool(pat.search(raw)) for name, pat in KEY_PATTERNS.items()}


def find_named_values(payload: Any, wanted: set[str]) -> list[dict[str, Any]]:
    """Recursively preserve named annotation fields and their JSON paths."""
    out: list[dict[str, Any]] = []

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                child = f"{path}.{key}" if path else key
                if key in wanted and not isinstance(value, (dict, list)):
                    out.append({"path": child, "field": key, "value": value})
                if isinstance(value, (dict, list)):
                    walk(value, child)
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                if isinstance(value, (dict, list)):
                    walk(value, f"{path}[{idx}]")

    walk(payload, "")
    return out


def directional_snpp_annotation(payload: Any, systematic_type: str) -> bool:
    """Require type and direction words inside the same term payload."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return bool(
        re.search(re.escape(systematic_type), raw, re.I)
        and re.search(r"flexion|extension", raw, re.I)
    )


def probe_record(status: int, payload: Any | None, url: str, error: str | None, *, max_records: int = 80) -> dict[str, Any]:
    return {
        "http_status": status,
        "url": url,
        "error": error,
        "flags": payload_flags(payload) if payload is not None else {},
        "manc_fields": find_named_values(payload, MANC_FIELD_NAMES) if payload is not None else [],
        "compact_hits": compact_hits(payload, max_records=max_records) if payload is not None else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/vfb_curated_identity_audit.json",
    )
    args = parser.parse_args()

    receipt: dict[str, Any] = {
        "schema": "neurofly-vfb-curated-identity-audit-v0.2",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "api_base": BASE,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "searches": {},
        "fanc_r21d12": {},
        "malecns_terms": {},
        "request_errors": [],
        "summary": {},
        "governance": {
            "curated_r21d12_fanc_hook_identity_found": False,
            "curated_fanc_to_malecns_snpp_bridge_found": False,
            "curated_directional_snpp_annotation_found": False,
            "exact_malecns_to_manc_body_fields_recovered": False,
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
        },
    }

    # Cached public search index. No force_refresh: the cached endpoint is the
    # public production surface and avoids turning one upstream refresh into a
    # whole-probe failure.
    for query in SEARCH_QUERIES:
        status, payload, url, error = fetch_json(
            "/search",
            {"query": query, "limit": 100},
        )
        receipt["searches"][query] = probe_record(status, payload, url, error)
        if error:
            receipt["request_errors"].append({"scope": f"search:{query}", "error": error, "url": url})

    # Curated R21D12/FANC identity.
    status, payload, url, error = fetch_json(
        "/get_term_info",
        {"id": FANC_R21D12_TERM},
    )
    fanc_term_payload = payload
    fanc_term = probe_record(status, payload, url, error, max_records=120)
    receipt["fanc_r21d12"]["term_info"] = fanc_term
    if error:
        receipt["request_errors"].append({"scope": "fanc:term_info", "error": error, "url": url})

    status, payload, url, error = fetch_json(
        "/xref",
        {"id": FANC_R21D12_TERM},
    )
    receipt["fanc_r21d12"]["xref_by_vfb_id"] = probe_record(status, payload, url, error, max_records=120)
    if error:
        receipt["request_errors"].append({"scope": "fanc:xref_vfb_id", "error": error, "url": url})

    status, payload, url, error = fetch_json(
        "/xref",
        {"accession": FANC_R21D12_NATIVE},
    )
    receipt["fanc_r21d12"]["xref_by_native_accession"] = probe_record(status, payload, url, error, max_records=120)
    if error:
        receipt["request_errors"].append({"scope": "fanc:xref_native", "error": error, "url": url})

    # Known MaleCNS systematic-type bodies. Preserve exact MANC body/group/type
    # fields when VFB exposes them.
    directional_by_term: dict[str, bool] = {}
    for systematic_type, body_map in KNOWN_MALECNS_TERMS.items():
        for body_id, vfb_id in body_map.items():
            status, payload, url, error = fetch_json(
                "/get_term_info",
                {"id": vfb_id},
            )
            key = f"{systematic_type}:{body_id}"
            rec = probe_record(status, payload, url, error, max_records=100)
            rec.update({
                "systematic_type": systematic_type,
                "body_id": int(body_id),
                "vfb_id": vfb_id,
            })
            receipt["malecns_terms"][key] = rec
            directional_by_term[key] = (
                directional_snpp_annotation(payload, systematic_type)
                if payload is not None
                else False
            )
            if error:
                receipt["request_errors"].append({"scope": f"malecns:{key}", "error": error, "url": url})

    fanc_raw = json.dumps(receipt["fanc_r21d12"], sort_keys=True, ensure_ascii=False)
    curated_fanc_hook = bool(
        re.search(r"R21D12", fanc_raw, re.I)
        and re.search(r"hook", fanc_raw, re.I)
        and re.search(r"570810|VFB_001028lx", fanc_raw, re.I)
    )
    fanc_to_malecns = bool(
        re.search(r"MaleCNS|male-cns", fanc_raw, re.I)
        and re.search(r"SNpp39|SNpp41", fanc_raw, re.I)
    )
    directional_snpp = any(directional_by_term.values())

    malecns_manc_body_fields = {
        key: [
            field for field in rec["manc_fields"]
            if field["field"] in {"mancBodyid", "mancBodyId", "manc_bodyid", "manc_body_id"}
        ]
        for key, rec in receipt["malecns_terms"].items()
    }
    malecns_manc_body_fields = {
        key: fields for key, fields in malecns_manc_body_fields.items() if fields
    }
    exact_manc_body_fields = bool(malecns_manc_body_fields)

    receipt["governance"]["curated_r21d12_fanc_hook_identity_found"] = curated_fanc_hook
    receipt["governance"]["curated_fanc_to_malecns_snpp_bridge_found"] = fanc_to_malecns
    receipt["governance"]["curated_directional_snpp_annotation_found"] = directional_snpp
    receipt["governance"]["exact_malecns_to_manc_body_fields_recovered"] = exact_manc_body_fields

    receipt["summary"] = {
        "search_query_count": len(SEARCH_QUERIES),
        "malecns_term_count": len(receipt["malecns_terms"]),
        "successful_malecns_term_requests": sum(
            1 for rec in receipt["malecns_terms"].values() if rec["http_status"] == 200
        ),
        "request_error_count": len(receipt["request_errors"]),
        "fanc_term_info_http_status": fanc_term["http_status"],
        "curated_r21d12_fanc_hook_identity_found": curated_fanc_hook,
        "curated_fanc_to_malecns_snpp_bridge_found": fanc_to_malecns,
        "curated_directional_snpp_annotation_found": directional_snpp,
        "exact_malecns_to_manc_body_fields_recovered": exact_manc_body_fields,
        "malecns_to_manc_body_fields": malecns_manc_body_fields,
        "directional_snpp_terms": [
            key for key, found in directional_by_term.items() if found
        ],
        "automatic_unlock_performed": False,
        "interpretation": (
            "The audit is cache-first and failure-tolerant. A curated R21D12/FANC "
            "hook identity strengthens the chain, but exact SNpp polarity remains "
            "locked unless an explicit curated FANC-to-MaleCNS SNpp bridge or "
            "directional SNpp annotation is recovered and independently reviewed."
        ),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PROBE_ERROR: {exc}", file=sys.stderr)
        raise
