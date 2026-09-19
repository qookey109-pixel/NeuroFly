#!/usr/bin/env python3
"""Read-only VFBquery audit for a curated FeCO hook polarity bridge.

This script queries the public VFBquery API for:
- SNpp39 / SNpp41 indexed terms,
- the curated R21D12/FANC hook neuron VFB_001028lx,
- known MaleCNS SNpp39 / SNpp41 bodies,
- xrefs for the FANC term and native accession.

It records evidence only. It never unlocks NeuroFly polarity/calibration/runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "https://v3-cached.virtualflybrain.org"
USER_AGENT = "NeuroFly-VFB-curated-identity-audit/0.1"
DECISION_POLICY = "evidence_only_no_auto_unlock"

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
    "GMR21D12",
    "570810",
    "hook chordotonal neuron R21D12",
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


def fetch_json(path: str, params: dict[str, Any] | None = None, timeout: int = 60) -> tuple[int, Any | None, str]:
    query = ("?" + urlencode(params, doseq=True)) if params else ""
    url = f"{BASE}{path}{query}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            return int(res.status), json.loads(raw), url
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:5000]}
        return int(exc.code), payload, url
    except URLError as exc:
        raise RuntimeError(f"network error for {url}: {exc}") from exc


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
                    "dataset", "type", "class", "subclass", "synonyms", "mancType",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/vfb_curated_identity_audit.json",
    )
    args = parser.parse_args()

    receipt: dict[str, Any] = {
        "schema": "neurofly-vfb-curated-identity-audit-v0.1",
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "api_base": BASE,
        "searches": {},
        "fanc_r21d12": {},
        "malecns_terms": {},
        "summary": {},
        "governance": {
            "curated_r21d12_fanc_hook_identity_found": False,
            "curated_fanc_to_malecns_snpp_bridge_found": False,
            "curated_directional_snpp_annotation_found": False,
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
        },
    }

    # Public search index
    for query in SEARCH_QUERIES:
        status, payload, url = fetch_json(
            "/search",
            {"query": query, "limit": 100, "force_refresh": "true"},
        )
        receipt["searches"][query] = {
            "http_status": status,
            "url": url,
            "flags": payload_flags(payload) if payload is not None else {},
            "compact_hits": compact_hits(payload) if payload is not None else [],
        }

    # Curated R21D12/FANC identity
    status, payload, url = fetch_json(
        "/get_term_info",
        {"id": FANC_R21D12_TERM, "force_refresh": "true"},
    )
    fanc_term = {
        "http_status": status,
        "url": url,
        "flags": payload_flags(payload) if payload is not None else {},
        "compact_hits": compact_hits(payload, max_records=120) if payload is not None else [],
    }
    receipt["fanc_r21d12"]["term_info"] = fanc_term

    status, payload, url = fetch_json(
        "/xref",
        {"id": FANC_R21D12_TERM, "force_refresh": "true"},
    )
    receipt["fanc_r21d12"]["xref_by_vfb_id"] = {
        "http_status": status,
        "url": url,
        "flags": payload_flags(payload) if payload is not None else {},
        "compact_hits": compact_hits(payload, max_records=120) if payload is not None else [],
    }

    status, payload, url = fetch_json(
        "/xref",
        {"accession": FANC_R21D12_NATIVE, "force_refresh": "true"},
    )
    receipt["fanc_r21d12"]["xref_by_native_accession"] = {
        "http_status": status,
        "url": url,
        "flags": payload_flags(payload) if payload is not None else {},
        "compact_hits": compact_hits(payload, max_records=120) if payload is not None else [],
    }

    # Known MaleCNS systematic-type bodies
    for systematic_type, body_map in KNOWN_MALECNS_TERMS.items():
        for body_id, vfb_id in body_map.items():
            status, payload, url = fetch_json(
                "/get_term_info",
                {"id": vfb_id, "force_refresh": "true"},
            )
            receipt["malecns_terms"][f"{systematic_type}:{body_id}"] = {
                "systematic_type": systematic_type,
                "body_id": int(body_id),
                "vfb_id": vfb_id,
                "http_status": status,
                "url": url,
                "flags": payload_flags(payload) if payload is not None else {},
                "compact_hits": compact_hits(payload, max_records=100) if payload is not None else [],
            }

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

    all_raw = json.dumps(receipt, sort_keys=True, ensure_ascii=False)
    directional_snpp = bool(
        re.search(r"SNpp39|SNpp41", all_raw, re.I)
        and re.search(r"flexion|extension", all_raw, re.I)
    )

    receipt["governance"]["curated_r21d12_fanc_hook_identity_found"] = curated_fanc_hook
    receipt["governance"]["curated_fanc_to_malecns_snpp_bridge_found"] = fanc_to_malecns
    receipt["governance"]["curated_directional_snpp_annotation_found"] = directional_snpp

    receipt["summary"] = {
        "search_query_count": len(SEARCH_QUERIES),
        "malecns_term_count": len(receipt["malecns_terms"]),
        "fanc_term_info_http_status": fanc_term["http_status"],
        "curated_r21d12_fanc_hook_identity_found": curated_fanc_hook,
        "curated_fanc_to_malecns_snpp_bridge_found": fanc_to_malecns,
        "curated_directional_snpp_annotation_found": directional_snpp,
        "automatic_unlock_performed": False,
        "interpretation": (
            "A curated R21D12/FANC hook identity is useful evidence, but exact "
            "SNpp polarity remains locked unless the API exposes an explicit "
            "curated FANC-to-MaleCNS SNpp bridge or directional SNpp annotation."
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
