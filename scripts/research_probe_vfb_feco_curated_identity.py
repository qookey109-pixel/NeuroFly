#!/usr/bin/env python3
"""Read-only curated-identity audit for the FeCO hook polarity gate.

Public sources:
1. VFBquery cached API for curated VFB/FANC/MaleCNS term metadata.
2. Public MaleCNS v1.0 DVID segmentation_annotations keys for exact
   MaleCNS -> MANC body/type provenance when exposed.

The audit is failure-tolerant and evidence-only. It never unlocks polarity,
calibration, or runtime stimulation automatically.
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


VFB_BASE = "https://v3-cached.virtualflybrain.org"
MCNS_DVID_BASE = "https://emdata-mcns.janelia.org"
MCNS_V1_ROOTNODE = "f3969dc575d74e4f922a8966709958c8"
MCNS_ANNOTATION_DATA = "segmentation_annotations"

USER_AGENT = "NeuroFly-VFB-curated-identity-audit/0.3"
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

SEARCH_QUERIES = [
    "SNpp39",
    "SNpp41",
    "R21D12",
    "570810",
    "SNpp39 MaleCNS",
    "SNpp41 MaleCNS",
]

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


def fetch_url_json(
    url: str,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> tuple[int, Any | None, str | None]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            return int(res.status), json.loads(raw), None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:5000]}
        return int(exc.code), payload, f"HTTPError:{exc.code}"
    except (URLError, TimeoutError, socket.timeout) as exc:
        return 0, None, f"{type(exc).__name__}:{exc}"


def fetch_vfb(
    path: str,
    params: dict[str, Any] | None = None,
) -> tuple[int, Any | None, str, str | None]:
    query = ("?" + urlencode(params, doseq=True)) if params else ""
    url = f"{VFB_BASE}{path}{query}"
    status, payload, error = fetch_url_json(url)
    return status, payload, url, error


def compact_hits(payload: Any, *, max_records: int = 80) -> list[dict[str, Any]]:
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
                    "description", "title", "Comment", "Name", "Types",
                ):
                    if key in obj and not isinstance(obj[key], (dict, list)):
                        summary[key] = obj[key]
                if len(summary) <= 2:
                    summary["preview"] = raw[:1200]
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


def parse_manc_fields_from_text(payload: Any) -> list[dict[str, Any]]:
    """Extract annotation fields embedded in VFB Meta.Comment prose."""
    raw = json.dumps(payload, ensure_ascii=False)
    out: list[dict[str, Any]] = []
    patterns = {
        "mancType": r"mancType\s*[-:=]\s*([^.,;\"]+)",
        "mancBodyid": r"mancBody(?:id|Id)\s*[-:=]\s*([0-9]+)",
        "mancGroup": r"mancGroup\s*[-:=]\s*([^.,;\"]+)",
    }
    for field, pattern in patterns.items():
        vals = sorted({m.group(1).strip() for m in re.finditer(pattern, raw, re.I)})
        for value in vals:
            out.append({"field": field, "value": value, "source": "embedded_text"})
    return out


def directional_snpp_annotation(payload: Any, systematic_type: str) -> bool:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return bool(
        re.search(re.escape(systematic_type), raw, re.I)
        and re.search(r"flexion|extension", raw, re.I)
    )


def probe_record(
    status: int,
    payload: Any | None,
    url: str,
    error: str | None,
    *,
    max_records: int = 80,
) -> dict[str, Any]:
    structured = find_named_values(payload, MANC_FIELD_NAMES) if payload is not None else []
    embedded = parse_manc_fields_from_text(payload) if payload is not None else []
    return {
        "http_status": status,
        "url": url,
        "error": error,
        "flags": payload_flags(payload) if payload is not None else {},
        "manc_fields": structured + embedded,
        "compact_hits": compact_hits(payload, max_records=max_records) if payload is not None else [],
    }


def dvid_annotation_url(body_id: int) -> str:
    return (
        f"{MCNS_DVID_BASE}/api/node/{MCNS_V1_ROOTNODE}/"
        f"{MCNS_ANNOTATION_DATA}/key/{body_id}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/vfb_curated_identity_audit.json",
    )
    args = parser.parse_args()

    receipt: dict[str, Any] = {
        "schema": "neurofly-vfb-curated-identity-audit-v0.3",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "vfb_api_base": VFB_BASE,
        "mcns_dvid": {
            "base": MCNS_DVID_BASE,
            "rootnode": MCNS_V1_ROOTNODE,
            "annotation_data": MCNS_ANNOTATION_DATA,
        },
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "searches": {},
        "fanc_r21d12": {},
        "malecns_terms": {},
        "malecns_dvid_annotations": {},
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

    for query in SEARCH_QUERIES:
        status, payload, url, error = fetch_vfb("/search", {"query": query, "limit": 100})
        receipt["searches"][query] = probe_record(status, payload, url, error)
        if error:
            receipt["request_errors"].append({"scope": f"search:{query}", "error": error, "url": url})

    fanc_payloads: list[Any] = []

    status, payload, url, error = fetch_vfb("/get_term_info", {"id": FANC_R21D12_TERM})
    fanc_payloads.append(payload)
    receipt["fanc_r21d12"]["term_info"] = probe_record(status, payload, url, error, max_records=120)
    if error:
        receipt["request_errors"].append({"scope": "fanc:term_info", "error": error, "url": url})

    status, payload, url, error = fetch_vfb("/xref", {"id": FANC_R21D12_TERM})
    fanc_payloads.append(payload)
    receipt["fanc_r21d12"]["xref_by_vfb_id"] = probe_record(status, payload, url, error, max_records=120)
    if error:
        receipt["request_errors"].append({"scope": "fanc:xref_vfb_id", "error": error, "url": url})

    status, payload, url, error = fetch_vfb("/xref", {"accession": FANC_R21D12_NATIVE})
    fanc_payloads.append(payload)
    receipt["fanc_r21d12"]["xref_by_native_accession"] = probe_record(status, payload, url, error, max_records=120)
    if error:
        receipt["request_errors"].append({"scope": "fanc:xref_native", "error": error, "url": url})

    directional_by_term: dict[str, bool] = {}
    for systematic_type, body_map in KNOWN_MALECNS_TERMS.items():
        for body_id_s, vfb_id in body_map.items():
            body_id = int(body_id_s)
            key = f"{systematic_type}:{body_id}"

            status, payload, url, error = fetch_vfb("/get_term_info", {"id": vfb_id})
            rec = probe_record(status, payload, url, error, max_records=100)
            rec.update({
                "systematic_type": systematic_type,
                "body_id": body_id,
                "vfb_id": vfb_id,
            })
            receipt["malecns_terms"][key] = rec
            directional_by_term[key] = (
                directional_snpp_annotation(payload, systematic_type)
                if payload is not None
                else False
            )
            if error:
                receipt["request_errors"].append({"scope": f"malecns-vfb:{key}", "error": error, "url": url})

            durl = dvid_annotation_url(body_id)
            dstatus, dpayload, derror = fetch_url_json(durl)
            drec = probe_record(dstatus, dpayload, durl, derror, max_records=60)
            drec.update({
                "systematic_type": systematic_type,
                "body_id": body_id,
            })
            receipt["malecns_dvid_annotations"][key] = drec
            if derror:
                receipt["request_errors"].append({"scope": f"malecns-dvid:{key}", "error": derror, "url": durl})

    # IMPORTANT: evaluate biological bridge flags against original endpoint
    # payloads/endpoint flags, never against the serialized receipt whose field
    # names contain words such as "malecns", "snpp39", etc.
    fanc_endpoint_flags = [
        payload_flags(p) for p in fanc_payloads if p is not None
    ]
    curated_fanc_hook = any(
        f["r21d12"] and f["fanc570810"] and f["hook"]
        for f in fanc_endpoint_flags
    )
    fanc_to_malecns = any(
        f["malecns"] and (f["snpp39"] or f["snpp41"])
        for f in fanc_endpoint_flags
    )
    directional_snpp = any(directional_by_term.values())

    exact_body_fields: dict[str, list[dict[str, Any]]] = {}
    for source_name in ("malecns_terms", "malecns_dvid_annotations"):
        for key, rec in receipt[source_name].items():
            fields = [
                field for field in rec["manc_fields"]
                if field["field"] in {
                    "mancBodyid", "mancBodyId", "manc_bodyid", "manc_body_id"
                }
                and str(field["value"]).strip() not in {"", "None", "null", "NA"}
            ]
            if fields:
                exact_body_fields.setdefault(key, []).extend(
                    [{**field, "source_record": source_name} for field in fields]
                )

    exact_manc_body_fields = bool(exact_body_fields)

    receipt["governance"]["curated_r21d12_fanc_hook_identity_found"] = curated_fanc_hook
    receipt["governance"]["curated_fanc_to_malecns_snpp_bridge_found"] = fanc_to_malecns
    receipt["governance"]["curated_directional_snpp_annotation_found"] = directional_snpp
    receipt["governance"]["exact_malecns_to_manc_body_fields_recovered"] = exact_manc_body_fields

    receipt["summary"] = {
        "search_query_count": len(SEARCH_QUERIES),
        "malecns_term_count": len(receipt["malecns_terms"]),
        "successful_malecns_vfb_requests": sum(
            1 for rec in receipt["malecns_terms"].values() if rec["http_status"] == 200
        ),
        "successful_malecns_dvid_requests": sum(
            1 for rec in receipt["malecns_dvid_annotations"].values() if rec["http_status"] == 200
        ),
        "request_error_count": len(receipt["request_errors"]),
        "curated_r21d12_fanc_hook_identity_found": curated_fanc_hook,
        "curated_fanc_to_malecns_snpp_bridge_found": fanc_to_malecns,
        "curated_directional_snpp_annotation_found": directional_snpp,
        "exact_malecns_to_manc_body_fields_recovered": exact_manc_body_fields,
        "malecns_to_manc_body_fields": exact_body_fields,
        "directional_snpp_terms": [
            key for key, found in directional_by_term.items() if found
        ],
        "automatic_unlock_performed": False,
        "interpretation": (
            "The audit combines curated VFB/FANC metadata with the public MaleCNS "
            "v1.0 DVID annotation keys. Exact polarity remains locked unless a "
            "curated FANC-to-MaleCNS SNpp bridge or explicit directional SNpp "
            "annotation is recovered and independently reviewed."
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
