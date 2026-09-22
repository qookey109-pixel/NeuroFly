#!/usr/bin/env python3
"""Read-only audit of the BANC 2026 cross-dataset FeCO identity bridge.

This probe does not recompute morphology. It reads author-published BANC
Supplementary Data 2 and the published BANC↔FANC v1.116 NBLAST product, then
checks whether the independently bridged SNpp41/MANC/MaleCNS neuron has any
author-validated FANC match.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

BANC_REPO = "htem/BANC-project"
BANC_COMMIT = "e31a2e26b9937dca72e5ca1c1960df6454d76114"
PIPELINE_REPO = "htem/bancpipeline"
PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"

SUPP_PATH = "manuscript/print/supplemental_data/supplemental_data_2.txt"
PIPELINE_SCHEMA_PATH = "banc/nblast/banc-nblast-cave.R"
SUPP_URL = (
    f"https://raw.githubusercontent.com/{BANC_REPO}/{BANC_COMMIT}/{SUPP_PATH}"
)
PIPELINE_SCHEMA_URL = (
    f"https://raw.githubusercontent.com/{PIPELINE_REPO}/{PIPELINE_COMMIT}/"
    f"{PIPELINE_SCHEMA_PATH}"
)
FANC_NBLAST_URL = (
    "https://storage.googleapis.com/"
    "lee-lab_brain-and-nerve-cord-fly-connectome/"
    "nblast/banc_fanc_1116_nblast.feather"
)

TARGET_BANC_ROOT = "720575941508169089"
TARGET_MANC_BODY = "97015"
TARGET_MALECNS_BODY = "911942"
TARGET_TYPE = "SNpp41"
TARGET_SUBCLASS = "middle_leg_hook_chordotonal_organ_neuron"
LEGACY_FANC_CATMAID_IDS = ["25849", "25842", "25856", "24831", "25909"]

RECEIPT_SCHEMA = "neurofly-banc-cross-dataset-bridge-audit-v0.1"
DECISION_POLICY = "evidence_only_no_auto_unlock"
USER_AGENT = "NeuroFly-BANC-bridge-audit/0.1"
TIMEOUT = 90


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=TIMEOUT) as res:
        return res.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def parse_supplement(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def supplement_bridge(rows: list[dict[str, str]]) -> dict[str, Any]:
    target = [r for r in rows if r.get("root_id") == TARGET_BANC_ROOT]
    manc = [r for r in rows if r.get("manc_match") == TARGET_MANC_BODY]
    malecns = [r for r in rows if r.get("malecns_match") == TARGET_MALECNS_BODY]

    exact = [
        r for r in target
        if r.get("cell_type") == TARGET_TYPE
        and r.get("cell_sub_class") == TARGET_SUBCLASS
        and r.get("manc_match") == TARGET_MANC_BODY
        and r.get("malecns_match") == TARGET_MALECNS_BODY
        and r.get("proofread") == "TRUE"
    ]
    return {
        "target_rows": target,
        "manc_97015_row_count": len(manc),
        "manc_97015_all_snpp41": bool(manc) and all(
            r.get("cell_type") == TARGET_TYPE for r in manc
        ),
        "manc_97015_all_middle_leg_hook": bool(manc) and all(
            r.get("cell_sub_class") == TARGET_SUBCLASS for r in manc
        ),
        "malecns_911942_rows": malecns,
        "exact_bridge_rows": exact,
        "independent_manc_malecns_bridge_confirmed": len(exact) == 1,
        "exact_bridge_fanc_match": exact[0].get("fanc_match") if exact else None,
    }


def pipeline_semantics(text: str) -> dict[str, Any]:
    normalized = " ".join(text.split())
    match_id_is_cell_id = (
        "match_id (FANC cell_id)" in text
        or "match_id (FANC cell_id)" in normalized
    )
    return {
        "fanc_match_id_semantics_confirmed": match_id_is_cell_id,
        "expected_semantics": "BANC match_id is FANC cell_id, not FANC root_id",
    }


def _truthy_validation(value: Any) -> bool:
    if value is True:
        return True
    return str(value).strip().lower() in {"t", "true", "1", "yes"}


def audit_fanc_feather(url: str) -> dict[str, Any]:
    # Lazy import keeps normal repository tests independent of pyarrow.
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather

    with tempfile.NamedTemporaryFile(suffix=".feather") as tmp:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=TIMEOUT) as res:
            while True:
                chunk = res.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        tmp.flush()
        table = feather.read_table(tmp.name)

    columns = table.column_names
    query_col = next(
        (c for c in ("pt_root_id", "query_root_id", "query_id", "root_id") if c in columns),
        None,
    )
    if query_col is None:
        return {
            "columns": columns,
            "error": "No recognized BANC query ID column",
            "target_rows": [],
            "validated_rows": [],
        }

    query_as_string = pc.cast(table[query_col], pa.string())
    filtered = table.filter(pc.equal(query_as_string, TARGET_BANC_ROOT))
    rows = filtered.to_pylist()

    validated = [
        row for row in rows
        if _truthy_validation(row.get("validation"))
    ]
    match_ids = sorted({
        str(row.get("match_id"))
        for row in validated
        if row.get("match_id") is not None
    })

    return {
        "columns": columns,
        "query_column": query_col,
        "target_row_count": len(rows),
        "target_rows": rows[:100],
        "validated_row_count": len(validated),
        "validated_rows": validated[:100],
        "validated_fanc_cell_ids": match_ids,
        "author_validated_fanc_match_found": bool(match_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/banc_cross_dataset_bridge_audit.json",
    )
    args = parser.parse_args()

    errors: list[dict[str, str]] = []

    try:
        supp_text = fetch_text(SUPP_URL)
        supp = supplement_bridge(parse_supplement(supp_text))
    except Exception as exc:
        errors.append({"scope": "supplemental_data_2", "error": repr(exc)})
        supp = {}

    try:
        schema_text = fetch_text(PIPELINE_SCHEMA_URL)
        semantics = pipeline_semantics(schema_text)
    except Exception as exc:
        errors.append({"scope": "pipeline_schema", "error": repr(exc)})
        semantics = {}

    try:
        fanc = audit_fanc_feather(FANC_NBLAST_URL)
    except Exception as exc:
        errors.append({"scope": "banc_fanc_1116_nblast", "error": repr(exc)})
        fanc = {
            "target_rows": [],
            "validated_rows": [],
            "validated_fanc_cell_ids": [],
            "author_validated_fanc_match_found": False,
        }

    validated_fanc = fanc.get("validated_fanc_cell_ids", [])
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "sources": {
            "banc_repository": BANC_REPO,
            "banc_commit": BANC_COMMIT,
            "supplement_path": SUPP_PATH,
            "pipeline_repository": PIPELINE_REPO,
            "pipeline_commit": PIPELINE_COMMIT,
            "pipeline_schema_path": PIPELINE_SCHEMA_PATH,
            "fanc_nblast_url": FANC_NBLAST_URL,
        },
        "targets": {
            "banc_root_id": TARGET_BANC_ROOT,
            "manc_body_id": TARGET_MANC_BODY,
            "malecns_body_id": TARGET_MALECNS_BODY,
            "type": TARGET_TYPE,
            "subclass": TARGET_SUBCLASS,
            "legacy_fanc_catmaid_ids": LEGACY_FANC_CATMAID_IDS,
        },
        "supplement_bridge": supp,
        "fanc_match_semantics": semantics,
        "banc_fanc_nblast": fanc,
        "summary": {
            "independent_manc_malecns_bridge_confirmed": bool(
                supp.get("independent_manc_malecns_bridge_confirmed")
            ),
            "supplement_exact_bridge_fanc_match": supp.get(
                "exact_bridge_fanc_match"
            ),
            "author_validated_current_fanc_match_found": bool(validated_fanc),
            "validated_current_fanc_cell_ids": validated_fanc,
            "legacy_to_current_fanc_namespace_resolved": False,
            "curated_r21d12_to_specific_fanc_em_identity_found": False,
            "curated_fanc_to_manc_snpp_bridge_found": False,
            "automatic_unlock_performed": False,
            "interpretation": (
                "BANC Supplementary Data 2 independently confirms the "
                "SNpp41 / MANC 97015 / MaleCNS 911942 bridge. Any validated "
                "FANC v1.116 match is reported separately. The older Phelps "
                "CATMAID source IDs are not equated with current FANC cell IDs "
                "without an explicit namespace bridge, and no R21D12 rank is "
                "promoted to curated one-cell identity."
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
        "request_errors": errors,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
