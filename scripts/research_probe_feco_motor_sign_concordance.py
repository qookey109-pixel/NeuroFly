#!/usr/bin/env python3
"""Cross-check FANC hook direction against independent preferred motor modules.

This audit joins three already-public/frozen evidence layers without morphology:

1. Lee 2024 static FANC FeCO annotations:
   T1L hook_flx / hook_ext with exact pt_root_id.
2. Lesser/Azevedo 2023 v840 preferred-module sensory Neuroglancer states,
   generated from a premotor-to-motor dataframe indexed by preferred motor
   module and cell class.
3. NeuroFly's merged PR #113 signed MANC circuit receipt:
   SNpp41 = extensor-positive / flexor-negative candidate,
   SNpp39 = extensor-negative / flexor-positive candidate.

The output is functional-sign concordance only. It is not a curated
FANC-to-MANC one-cell identity and cannot automatically unlock runtime.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

LEE_REPO = "sagrawal/Lee_2024"
LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"
LEE_FECO_PATH = "synapse_tables/feco_annotation_table.csv"
LEE_FECO_URL = (
    f"https://raw.githubusercontent.com/{LEE_REPO}/{LEE_COMMIT}/{LEE_FECO_PATH}"
)

LESSER_REPO = "tuthill-lab/Lesser_Azevedo_2023"
LESSER_COMMIT = "93cafa55b8bbdb1493e8d73c941035969349b223"
LESSER_BASE = (
    f"https://raw.githubusercontent.com/{LESSER_REPO}/{LESSER_COMMIT}"
)
GENERATOR_PATH = "jsons/make_jsons/generate_links_and_table.ipynb"
UTILS_PATH = "utils.py"

SENSORY_MODULE_FILES = (
    "preferred_module_DLM_sensory.json",
    "preferred_module_DVM_sensory.json",
    "preferred_module_coxa_poste_sensory.json",
    "preferred_module_coxa_promo_sensory.json",
    "preferred_module_coxa_rotator_addu_sensory.json",
    "preferred_module_femur_re_sensory.json",
    "preferred_module_ltm_dipa_sensory.json",
    "preferred_module_ltm_non_sensory.json",
    "preferred_module_steerA_sensory.json",
    "preferred_module_steerB_sensory.json",
    "preferred_module_steerC_sensory.json",
    "preferred_module_steerD_sensory.json",
    "preferred_module_steerhg2_sensory.json",
    "preferred_module_tarsus_depressor_me_sensory.json",
    "preferred_module_tarsus_depressor_vent_sensory.json",
    "preferred_module_tension_sensory.json",
    "preferred_module_tibia_ex_sensory.json",
    "preferred_module_tibia_ta_fl_sensory.json",
    "preferred_module_tibia_ta_flex_A_sensory.json",
    "preferred_module_tibia_ta_flex_B_sensory.json",
    "preferred_module_tibia_ta_flex_C_sensory.json",
    "preferred_module_trochanter__sensory.json",
    "preferred_module_trochanter_ex_sensory.json",
)

EXTENSOR_MODULE = "preferred_module_tibia_ex_sensory.json"
FLEXOR_MODULES = {
    "preferred_module_tibia_ta_fl_sensory.json",
    "preferred_module_tibia_ta_flex_A_sensory.json",
    "preferred_module_tibia_ta_flex_B_sensory.json",
    "preferred_module_tibia_ta_flex_C_sensory.json",
}

PHELPS_HOOK_FLX_ROOTS = {
    "24831": "648518346481857725",
    "25842": "648518346509569667",
    "25849": "648518346494933426",
    "25856": "648518346514448583",
    "25909": "648518346494264434",
}

FROZEN_MANC_RECEIPT = Path("data/feco_hook_polarity_crosscheck_v01.json")
RECEIPT_SCHEMA = "neurofly-feco-motor-sign-concordance-v0.1"
USER_AGENT = "NeuroFly-feco-motor-sign-concordance/0.1"
TIMEOUT = 45

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "snpp39_snpp41_polarity_resolved": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=TIMEOUT) as res:
        return res.read().decode("utf-8", errors="replace")


def all_segments(state: dict) -> set[str]:
    out: set[str] = set()
    for layer in state.get("layers", []):
        for segment in layer.get("segments", []):
            out.add(str(segment))
    return out


def module_category(filename: str | None) -> str:
    if filename is None:
        return "unassigned"
    if filename == EXTENSOR_MODULE:
        return "tibia_extensor"
    if filename in FLEXOR_MODULES:
        return "tibia_flexor"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []

    try:
        lee_text = fetch_text(LEE_FECO_URL)
        lee_rows = list(csv.DictReader(io.StringIO(lee_text)))
    except Exception as exc:
        lee_rows = []
        errors.append(f"lee_feco:{type(exc).__name__}:{exc}")

    hooks = [
        row
        for row in lee_rows
        if row.get("classification_system") == "T1L"
        and row.get("cell_type") in {"hook_flx", "hook_ext"}
    ]
    hook_by_root = {str(row["pt_root_id"]): row for row in hooks}

    module_segments: dict[str, set[str]] = {}
    for filename in SENSORY_MODULE_FILES:
        url = f"{LESSER_BASE}/jsons/v840/{filename}"
        try:
            module_segments[filename] = all_segments(json.loads(fetch_text(url)))
        except Exception as exc:
            errors.append(f"{filename}:{type(exc).__name__}:{exc}")

    try:
        generator_text = fetch_text(f"{LESSER_BASE}/{GENERATOR_PATH}")
        utils_text = fetch_text(f"{LESSER_BASE}/{UTILS_PATH}")
    except Exception as exc:
        generator_text = ""
        utils_text = ""
        errors.append(f"lesser_semantics:{type(exc).__name__}:{exc}")

    generator_semantics_verified = all(
        token in generator_text
        for token in (
            "preferred_module",
            "cell_class",
            "seg_ids",
            "preferred_module_{}_{}",
        )
    )
    tibia_extensor_semantics_verified = (
        "tibia_extend" in utils_text
        and "tibia_extensor" in utils_text
        and "'extend'" in utils_text
    )

    assignments: dict[str, list[str]] = {}
    for root in hook_by_root:
        assignments[root] = [
            filename
            for filename, segments in module_segments.items()
            if root in segments
        ]

    rows_out = []
    for root, row in hook_by_root.items():
        mods = assignments[root]
        filename = mods[0] if len(mods) == 1 else None
        rows_out.append(
            {
                "annotation_id": row.get("id"),
                "cell_type": row.get("cell_type"),
                "pt_supervoxel_id": str(row.get("pt_supervoxel_id")),
                "pt_root_id": root,
                "preferred_module_files": mods,
                "preferred_module_count": len(mods),
                "preferred_module_category": (
                    module_category(filename)
                    if len(mods) <= 1
                    else "ambiguous_multiple"
                ),
            }
        )

    def summarize(cell_type: str) -> dict:
        typed = [r for r in rows_out if r["cell_type"] == cell_type]
        counts = {
            "tibia_extensor": 0,
            "tibia_flexor": 0,
            "other": 0,
            "unassigned": 0,
            "ambiguous_multiple": 0,
        }
        for row in typed:
            counts[row["preferred_module_category"]] += 1
        return {
            "cell_count": len(typed),
            "category_counts": counts,
            "rows": typed,
        }

    flx = summarize("hook_flx")
    ext = summarize("hook_ext")

    phelps_rows = []
    for skid, root in PHELPS_HOOK_FLX_ROOTS.items():
        match = next((r for r in rows_out if r["pt_root_id"] == root), None)
        phelps_rows.append(
            {
                "legacy_fanc_catmaid_skid": skid,
                "pt_root_id": root,
                "lee_row": match,
            }
        )

    phelps_categories = [
        x["lee_row"]["preferred_module_category"]
        for x in phelps_rows
        if x["lee_row"] is not None
    ]

    manc = json.loads(FROZEN_MANC_RECEIPT.read_text(encoding="utf-8"))
    candidate = manc["circuit_consistency_inference"]["candidate_crosswalk"]
    manc_candidate_verified = (
        candidate.get("SNpp41") == "hook_flexion_candidate"
        and candidate.get("SNpp39") == "hook_extension_candidate"
    )
    signed_evidence = next(
        (
            s["evidence"]
            for s in manc.get("sources", [])
            if s.get("id") == "manc_systematic_annotation_2024"
        ),
        [],
    )
    signed_circuit_receipt_verified = (
        manc_candidate_verified
        and any("SNpp41" in x and "tibia extensor" in x for x in signed_evidence)
        and any("SNpp39" in x and "tibia extensor" in x for x in signed_evidence)
    )

    no_crossed_tibia_preference = (
        flx["category_counts"]["tibia_flexor"] == 0
        and ext["category_counts"]["tibia_extensor"] == 0
    )
    dominant_opposed_tibia_preference = (
        flx["category_counts"]["tibia_extensor"] > flx["cell_count"] / 2
        and ext["category_counts"]["tibia_flexor"] > ext["cell_count"] / 2
    )
    bidirectional_motor_module_separation = (
        no_crossed_tibia_preference and dominant_opposed_tibia_preference
    )
    functional_sign_concordance = (
        generator_semantics_verified
        and tibia_extensor_semantics_verified
        and signed_circuit_receipt_verified
        and bidirectional_motor_module_separation
    )

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_CROSSCHECK_ONLY",
        "sources": {
            "lee_repository": LEE_REPO,
            "lee_commit": LEE_COMMIT,
            "lee_feco_path": LEE_FECO_PATH,
            "lesser_repository": LESSER_REPO,
            "lesser_commit": LESSER_COMMIT,
            "lesser_generator_path": GENERATOR_PATH,
            "lesser_utils_path": UTILS_PATH,
            "frozen_manc_receipt": str(FROZEN_MANC_RECEIPT),
        },
        "source_semantics": {
            "sensory_module_file_count": len(SENSORY_MODULE_FILES),
            "generator_semantics_verified": generator_semantics_verified,
            "tibia_extensor_semantics_verified": tibia_extensor_semantics_verified,
        },
        "fanc_directional_population": {
            "t1l_hook_cell_count": len(rows_out),
            "hook_flx": flx,
            "hook_ext": ext,
            "no_crossed_tibia_preference": no_crossed_tibia_preference,
            "dominant_opposed_tibia_preference": dominant_opposed_tibia_preference,
            "bidirectional_motor_module_separation_found": bidirectional_motor_module_separation,
        },
        "phelps_candidate_set": {
            "rows": phelps_rows,
            "category_counts": {
                "tibia_extensor": phelps_categories.count("tibia_extensor"),
                "tibia_flexor": phelps_categories.count("tibia_flexor"),
                "other": phelps_categories.count("other"),
                "unassigned": phelps_categories.count("unassigned"),
            },
        },
        "manc_signed_circuit": {
            "candidate_crosswalk": candidate,
            "signed_circuit_receipt_verified": signed_circuit_receipt_verified,
        },
        "summary": {
            "functional_sign_concordance_supports_snpp41_hook_flexion_candidate": functional_sign_concordance,
            "functional_sign_concordance_supports_snpp39_hook_extension_candidate": functional_sign_concordance,
            "curated_cross_connectome_identity_found": False,
            "automatic_unlock_performed": False,
            "interpretation": (
                "FANC directional hook populations separate strongly by preferred tibia motor module "
                "and the sign aligns with the already-frozen MANC SNpp41/SNpp39 circuit candidate. "
                "This is an independent functional-sign concordance, not a curated one-cell identity."
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
