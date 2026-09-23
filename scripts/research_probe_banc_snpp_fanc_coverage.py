#!/usr/bin/env python3
"""Audit all BANC SNpp39/SNpp41 rows for published FANC matches.

A prior ad-hoc check incorrectly split Supplementary Data 2 on tabs. The
published .txt content is CSV-like and the earlier NeuroFly #121 audit
successfully parsed it with csv.DictReader's comma default. This probe
explicitly detects the dialect and freezes all relevant SNpp39/SNpp41 rows.

The strongest positive candidate is deliberately narrow: an exact published
row with MANC match 97015 (or MaleCNS 911942), SNpp41 hook identity, and a
non-missing FANC match. Any weaker same-type/other-segment FANC match is reported
but never promoted across segments by name alone.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BANC_REPO = "htem/BANC-project"
BANC_COMMIT = "e31a2e26b9937dca72e5ca1c1960df6454d76114"
SUPP_PATH = "manuscript/print/supplemental_data/supplemental_data_2.txt"
SUPP_URL = (
    f"https://raw.githubusercontent.com/{BANC_REPO}/{BANC_COMMIT}/{SUPP_PATH}"
)
FANC_NBLAST_URL = (
    "https://storage.googleapis.com/"
    "lee-lab_brain-and-nerve-cord-fly-connectome/"
    "nblast/banc_fanc_1116_nblast.feather"
)

TARGET_TYPES = {"SNpp39", "SNpp41"}
TARGET_BANC_ROOT = "720575941508169089"
TARGET_MANC_BODY = "97015"
TARGET_MALECNS_BODY = "911942"
TARGET_SUBCLASS = "middle_leg_hook_chordotonal_organ_neuron"

RECEIPT_SCHEMA = "neurofly-banc-snpp-fanc-coverage-audit-v0.1"
USER_AGENT = "NeuroFly-banc-snpp-fanc-coverage-audit/0.1"
TIMEOUT = 45

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}

MISSING = {"", "NA", "N/A", "NULL", "NONE", "NAN"}


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=TIMEOUT) as res:
        return res.read().decode("utf-8", errors="replace")


def nonmissing(value: object) -> bool:
    return str(value or "").strip().upper() not in MISSING


def clean_row(row: dict[str, str]) -> dict[str, str]:
    return {str(k): str(v or "").strip() for k, v in row.items() if k is not None}


def parse_rows(text: str) -> tuple[list[dict[str, str]], str]:
    sample = text[:16384]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows = [
        clean_row(r)
        for r in csv.DictReader(io.StringIO(text), delimiter=delimiter)
    ]
    return rows, delimiter


def truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"t", "true", "1", "yes"}


def audit_fanc_nblast(banc_rows: list[dict[str, str]]) -> dict[str, object]:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather

    wanted = {
        (r.get("root_id", ""), r.get("fanc_match", ""))
        for r in banc_rows
        if nonmissing(r.get("fanc_match"))
        and "_hook_chordotonal_organ_neuron" in r.get("cell_sub_class", "")
        and r.get("proofread") == "TRUE"
    }
    wanted_roots = {root for root, _ in wanted}
    wanted_matches = {match for _, match in wanted}

    with tempfile.NamedTemporaryFile(suffix=".feather") as tmp:
        req = Request(FANC_NBLAST_URL, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=TIMEOUT) as res:
            while True:
                chunk = res.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        tmp.flush()
        table = feather.read_table(tmp.name)

    query_col = "pt_root_id" if "pt_root_id" in table.column_names else "query_root_id"
    qstr = pc.cast(table[query_col], pa.string())
    filtered = table.filter(pc.is_in(qstr, value_set=pa.array(sorted(wanted_roots))))
    rows = filtered.to_pylist()

    exact_rows = []
    banc_by_pair = {
        (r.get("root_id", ""), r.get("fanc_match", "")): r
        for r in banc_rows
        if (r.get("root_id", ""), r.get("fanc_match", "")) in wanted
    }
    for row in rows:
        qroot = str(row.get(query_col) or "")
        mid = str(row.get("match_id") or "")
        pair = (qroot, mid)
        if pair not in wanted:
            continue
        br = banc_by_pair[pair]
        exact_rows.append(
            {
                "banc_root_id": qroot,
                "banc_cell_type": br.get("cell_type"),
                "banc_cell_sub_class": br.get("cell_sub_class"),
                "banc_body_part_sensory": br.get("body_part_sensory"),
                "banc_side": br.get("side"),
                "banc_fanc_match": mid,
                "banc_manc_match": br.get("manc_match"),
                "banc_malecns_match": br.get("malecns_match"),
                "nblast_match_cell_type": row.get("match_cell_type"),
                "nblast_score": row.get("score"),
                "nblast_validation": truthy(row.get("validation")),
            }
        )

    validated = [r for r in exact_rows if r["nblast_validation"]]
    by_type = {}
    for typ in ("SNpp39", "SNpp41"):
        tr = [r for r in validated if r["banc_cell_type"] == typ]
        labels = sorted({
            str(r["nblast_match_cell_type"])
            for r in tr
            if r["nblast_match_cell_type"] is not None
            and str(r["nblast_match_cell_type"]).strip()
        })
        by_type[typ] = {
            "validated_exact_join_count": len(tr),
            "match_cell_types": labels,
            "rows": tr,
        }

    labels39 = by_type["SNpp39"]["match_cell_types"]
    labels41 = by_type["SNpp41"]["match_cell_types"]
    directional = (
        by_type["SNpp39"]["validated_exact_join_count"] >= 2
        and by_type["SNpp41"]["validated_exact_join_count"] >= 2
        and len(labels39) == 1
        and len(labels41) == 1
        and labels39 != labels41
        and labels39[0] in {"hook_ext", "hook_flx"}
        and labels41[0] in {"hook_ext", "hook_flx"}
    )

    return {
        "source_url": FANC_NBLAST_URL,
        "columns": table.column_names,
        "wanted_hook_pair_count": len(wanted),
        "wanted_fanc_match_ids": sorted(wanted_matches),
        "exact_join_rows": exact_rows,
        "exact_join_count": len(exact_rows),
        "validated_exact_join_count": len(validated),
        "validated_by_banc_type": by_type,
        "replicated_directional_type_crosswalk_candidate_found": directional,
    }


def select_fields(row: dict[str, str]) -> dict[str, str]:
    keys = (
        "root_id",
        "cell_type",
        "cell_sub_class",
        "cell_class",
        "cell_function",
        "cell_function_detailed",
        "body_part_sensory",
        "side",
        "nerve",
        "proofread",
        "roughly_proofread",
        "fanc_match",
        "manc_match",
        "malecns_match",
        "fafb_match",
        "hemibrain_match",
        "other_names",
    )
    return {k: row.get(k, "") for k in keys}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    text = fetch_text(SUPP_URL)
    rows, delimiter = parse_rows(text)

    snpp_rows = [r for r in rows if r.get("cell_type") in TARGET_TYPES]
    snpp39 = [r for r in snpp_rows if r.get("cell_type") == "SNpp39"]
    snpp41 = [r for r in snpp_rows if r.get("cell_type") == "SNpp41"]

    snpp39_fanc = [r for r in snpp39 if nonmissing(r.get("fanc_match"))]
    snpp41_fanc = [r for r in snpp41 if nonmissing(r.get("fanc_match"))]
    snpp39_fanc_ids = {r.get("fanc_match", "") for r in snpp39_fanc}
    snpp41_fanc_ids = {r.get("fanc_match", "") for r in snpp41_fanc}
    cross_type_fanc_ids = sorted(snpp39_fanc_ids.intersection(snpp41_fanc_ids))

    target_banc = [r for r in rows if r.get("root_id") == TARGET_BANC_ROOT]
    manc_97015 = [r for r in rows if r.get("manc_match") == TARGET_MANC_BODY]
    malecns_911942 = [
        r for r in rows if r.get("malecns_match") == TARGET_MALECNS_BODY
    ]

    exact_same_row_bridge = [
        r
        for r in rows
        if r.get("cell_type") == "SNpp41"
        and r.get("cell_sub_class") == TARGET_SUBCLASS
        and r.get("manc_match") == TARGET_MANC_BODY
        and r.get("malecns_match") == TARGET_MALECNS_BODY
        and nonmissing(r.get("fanc_match"))
    ]

    target_banc_with_fanc = [
        r for r in target_banc if nonmissing(r.get("fanc_match"))
    ]
    manc_with_fanc = [r for r in manc_97015 if nonmissing(r.get("fanc_match"))]
    malecns_with_fanc = [
        r for r in malecns_911942 if nonmissing(r.get("fanc_match"))
    ]

    # This is context only. A FANC match on another SNpp41/SNpp39 row is not
    # transferred across legs/sides by type name.
    other_snpp_fanc_context = [
        select_fields(r)
        for r in [*snpp39_fanc, *snpp41_fanc]
        if r.get("root_id") != TARGET_BANC_ROOT
    ]

    fanc_nblast_join = audit_fanc_nblast(snpp_rows)

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "repository": BANC_REPO,
            "commit": BANC_COMMIT,
            "path": SUPP_PATH,
            "url": SUPP_URL,
            "detected_delimiter": delimiter,
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
        },
        "targets": {
            "banc_root_id": TARGET_BANC_ROOT,
            "manc_body_id": TARGET_MANC_BODY,
            "malecns_body_id": TARGET_MALECNS_BODY,
            "target_type": "SNpp41",
            "target_subclass": TARGET_SUBCLASS,
        },
        "snpp_coverage": {
            "snpp39_row_count": len(snpp39),
            "snpp41_row_count": len(snpp41),
            "snpp39_fanc_match_count": len(snpp39_fanc),
            "snpp41_fanc_match_count": len(snpp41_fanc),
            "snpp39_unique_fanc_match_ids": sorted(snpp39_fanc_ids),
            "snpp41_unique_fanc_match_ids": sorted(snpp41_fanc_ids),
            "cross_type_fanc_match_ids": cross_type_fanc_ids,
            "cross_type_fanc_match_id_count": len(cross_type_fanc_ids),
            "snpp39_rows": [select_fields(r) for r in snpp39],
            "snpp41_rows": [select_fields(r) for r in snpp41],
            "other_snpp_fanc_context": other_snpp_fanc_context,
        },
        "fanc_nblast_join": fanc_nblast_join,
        "exact_target_coverage": {
            "target_banc_row_count": len(target_banc),
            "target_banc_rows": [select_fields(r) for r in target_banc],
            "target_banc_with_fanc_match_count": len(target_banc_with_fanc),
            "manc_97015_row_count": len(manc_97015),
            "manc_97015_with_fanc_match_count": len(manc_with_fanc),
            "manc_97015_with_fanc_rows": [select_fields(r) for r in manc_with_fanc],
            "malecns_911942_row_count": len(malecns_911942),
            "malecns_911942_with_fanc_match_count": len(malecns_with_fanc),
            "malecns_911942_with_fanc_rows": [
                select_fields(r) for r in malecns_with_fanc
            ],
            "exact_same_row_bridge_count": len(exact_same_row_bridge),
            "exact_same_row_bridge_rows": [
                select_fields(r) for r in exact_same_row_bridge
            ],
        },
        "summary": {
            "csv_parse_succeeded": bool(rows),
            "snpp_rows_found": bool(snpp_rows),
            "any_snpp39_fanc_match_found": bool(snpp39_fanc),
            "any_snpp41_fanc_match_found": bool(snpp41_fanc),
            "cross_type_fanc_match_ambiguity_found": bool(cross_type_fanc_ids),
            "target_banc_fanc_match_found": bool(target_banc_with_fanc),
            "manc_97015_fanc_match_found": bool(manc_with_fanc),
            "malecns_911942_fanc_match_found": bool(malecns_with_fanc),
            "exact_same_row_snpp41_manc_malecns_fanc_bridge_found": bool(
                exact_same_row_bridge
            ),
            "replicated_directional_type_crosswalk_candidate_found": bool(
                fanc_nblast_join.get(
                    "replicated_directional_type_crosswalk_candidate_found"
                )
            ),
            "interpretation": (
                "Only an exact same published row joining SNpp41 hook identity, "
                "MANC 97015 or MaleCNS 911942, and a non-missing FANC match can "
                "be considered a direct cross-dataset bridge candidate. FANC "
                "matches on other SNpp39/SNpp41 instances are context only and "
                "are not transferred across legs/sides by type name."
            ),
        },
        "locks": LOCKS,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
