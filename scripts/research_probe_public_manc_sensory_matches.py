#!/usr/bin/env python3
"""Read-only audit of the author-published public MANC sensory-match CSV.

This probe tests whether the public file explicitly bridges the frozen MANC
SNpp41 identity (MANC 97015) to either:
- the BANC-published FANC candidate cell_id 20201, or
- one of the five current FANC hook_flx roots frozen by PR #124.

No morphology, proximity, root inference, or same-number inference is allowed.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PIPELINE_REPO = "htem/bancpipeline"
PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"
PIPELINE_UPLOAD_PATH = "setup/hms_setup.R"
PIPELINE_UPLOAD_URL = (
    f"https://raw.githubusercontent.com/{PIPELINE_REPO}/{PIPELINE_COMMIT}/"
    f"{PIPELINE_UPLOAD_PATH}"
)

PUBLIC_MATCH_URL = (
    "https://storage.googleapis.com/"
    "lee-lab_brain-and-nerve-cord-fly-connectome/"
    "neuron_searches/2024-09-02_manc_sensory_matches.csv"
)
PUBLIC_MATCH_FILENAME = "2024-09-02_manc_sensory_matches.csv"

TARGET_MANC_BODY = "97015"
TARGET_TYPE = "SNpp41"
TARGET_FANC_CELL_ID = "20201"
TARGET_FANC_ROOTS = {
    "648518346481857725",
    "648518346509569667",
    "648518346494933426",
    "648518346514448583",
    "648518346494264434",
}

RECEIPT_SCHEMA = "neurofly-public-manc-sensory-match-audit-v0.1"
USER_AGENT = "NeuroFly-public-manc-sensory-match-audit/0.1"
TIMEOUT = 30

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


def normalize(value: object) -> str:
    return str(value or "").strip()


def exact_token_hits(row: dict[str, str], tokens: set[str]) -> dict[str, str]:
    return {
        key: normalize(value)
        for key, value in row.items()
        if normalize(value) in tokens
    }


def row_has(row: dict[str, str], token: str) -> bool:
    return any(normalize(v) == token for v in row.values())


def compact_row(row: dict[str, str]) -> dict[str, str]:
    return {k: normalize(v) for k, v in row.items() if normalize(v)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    errors: list[dict[str, str]] = []

    try:
        upload_source = fetch_text(PIPELINE_UPLOAD_URL)
        upload_path_verified = (
            PUBLIC_MATCH_FILENAME in upload_source
            and "lee-lab_brain-and-nerve-cord-fly-connectome/neuron_searches" in upload_source
        )
    except Exception as exc:
        upload_source = ""
        upload_path_verified = False
        errors.append({"scope": "pipeline_upload_source", "error": repr(exc)})

    try:
        csv_text = fetch_text(PUBLIC_MATCH_URL)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = [dict(r) for r in reader]
        fieldnames = list(reader.fieldnames or [])
    except Exception as exc:
        rows = []
        fieldnames = []
        errors.append({"scope": "public_match_csv", "error": repr(exc)})

    tokens = {
        TARGET_MANC_BODY,
        TARGET_TYPE,
        TARGET_FANC_CELL_ID,
        *TARGET_FANC_ROOTS,
    }

    target_rows = []
    for idx, row in enumerate(rows):
        hits = exact_token_hits(row, tokens)
        if hits:
            target_rows.append(
                {
                    "row_index": idx,
                    "exact_hits": hits,
                    "row": compact_row(row),
                }
            )

    rows_with_manc_body = [x for x in target_rows if row_has(x["row"], TARGET_MANC_BODY)]
    rows_with_type = [x for x in target_rows if row_has(x["row"], TARGET_TYPE)]
    rows_with_cell_id = [x for x in target_rows if row_has(x["row"], TARGET_FANC_CELL_ID)]
    rows_with_fanc_root = [
        x
        for x in target_rows
        if any(row_has(x["row"], root) for root in TARGET_FANC_ROOTS)
    ]

    same_row_manc_to_cell_id = [
        x
        for x in target_rows
        if row_has(x["row"], TARGET_MANC_BODY)
        and row_has(x["row"], TARGET_FANC_CELL_ID)
    ]
    same_row_manc_to_current_root = [
        x
        for x in target_rows
        if row_has(x["row"], TARGET_MANC_BODY)
        and any(row_has(x["row"], root) for root in TARGET_FANC_ROOTS)
    ]
    same_row_type_to_current_root = [
        x
        for x in target_rows
        if row_has(x["row"], TARGET_TYPE)
        and any(row_has(x["row"], root) for root in TARGET_FANC_ROOTS)
    ]

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "pipeline_repository": PIPELINE_REPO,
            "pipeline_commit": PIPELINE_COMMIT,
            "pipeline_upload_path": PIPELINE_UPLOAD_PATH,
            "pipeline_upload_path_verified": upload_path_verified,
            "public_match_url": PUBLIC_MATCH_URL,
            "public_match_filename": PUBLIC_MATCH_FILENAME,
            "csv_row_count": len(rows),
            "csv_columns": fieldnames,
        },
        "targets": {
            "manc_body_id": TARGET_MANC_BODY,
            "systematic_type": TARGET_TYPE,
            "banc_fanc_candidate_cell_id": TARGET_FANC_CELL_ID,
            "hook_flx_current_fanc_roots": sorted(TARGET_FANC_ROOTS),
        },
        "matches": {
            "rows_with_exact_target_tokens": target_rows,
            "rows_with_manc_97015_count": len(rows_with_manc_body),
            "rows_with_snpp41_count": len(rows_with_type),
            "rows_with_fanc_cell_id_20201_count": len(rows_with_cell_id),
            "rows_with_hook_flx_current_root_count": len(rows_with_fanc_root),
            "same_row_manc_97015_and_fanc_cell_20201_count": len(same_row_manc_to_cell_id),
            "same_row_manc_97015_and_hook_flx_root_count": len(same_row_manc_to_current_root),
            "same_row_snpp41_and_hook_flx_root_count": len(same_row_type_to_current_root),
            "same_row_manc_97015_and_fanc_cell_20201": same_row_manc_to_cell_id,
            "same_row_manc_97015_and_hook_flx_root": same_row_manc_to_current_root,
            "same_row_snpp41_and_hook_flx_root": same_row_type_to_current_root,
        },
        "summary": {
            "public_source_fetch_succeeded": bool(rows),
            "author_publish_path_verified": upload_path_verified,
            "direct_exact_public_manc_to_fanc_cell_id_bridge_found": bool(same_row_manc_to_cell_id),
            "direct_exact_public_manc_to_hook_flx_root_bridge_found": bool(same_row_manc_to_current_root),
            "direct_exact_public_snpp41_to_hook_flx_root_bridge_found": bool(same_row_type_to_current_root),
            "interpretation": (
                "Only exact token co-occurrence in one author-published sensory-match row "
                "is reported as a direct bridge candidate. This audit never upgrades a "
                "candidate to curated identity or opens polarity/runtime/calibration locks."
            ),
        },
        "locks": LOCKS,
        "request_errors": errors,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
