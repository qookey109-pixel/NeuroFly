from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "neurofly-snpp39-snpp41-polarity-crosswalk-audit-v1"
STATUS_DISCOVERY = "DISCOVERY_REQUIRED"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_FAIL = "FAIL"

LEE_REPOSITORY = "sagrawal/Lee_2024"
LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"
LEE_TABLE_BLOB_SHA1 = "3346a13fa31af8779eb39b277c443a252ff86115"
LEE_TABLE_URL = (
    "https://raw.githubusercontent.com/sagrawal/Lee_2024/"
    f"{LEE_COMMIT}/synapse_tables/feco_annotation_table.csv"
)
LEE_EXPECTED_COUNTS = {"hook_flx": 13, "hook_ext": 9}

BANC_PROJECT_REPOSITORY = "htem/BANC-project"
BANC_PROJECT_COMMIT = "e31a2e26b9937dca72e5ca1c1960df6454d76114"
BANC_META_URL = (
    "https://storage.googleapis.com/lee-lab_brain-and-nerve-cord-fly-connectome/"
    "compiled_data/banc_888/banc_888_meta.feather"
)
BANC_META_EXPECTED_MD5 = "8c8babff28b21c57ecc999e664560ef5"
BANC_META_EXPECTED_SIZE = 51450978
BANC_FANC_NBLAST_URL = (
    "https://storage.googleapis.com/lee-lab_brain-and-nerve-cord-fly-connectome/"
    "nblast/banc_fanc_1116_nblast.feather"
)
BANC_FANC_NBLAST_EXPECTED_SIZE = 93624386

SYSTEMATIC_TYPES = ("SNpp39", "SNpp41")
HOOK_TUNINGS = ("hook_flx", "hook_ext")
EXPECTED_RECEIPT_SHA256: str | None = None


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroFly/0.4 polarity-crosswalk-audit"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    if destination.stat().st_size == 0:
        raise ValueError(f"Downloaded file is empty: {url}")


def _file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalise_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().lower() in {"true", "t", "1", "yes", "y"}


def parse_lee_hook_rows(csv_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"valid", "classification_system", "cell_type", "pt_root_id"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("Lee FeCO table is missing required columns")
    for row in reader:
        tuning = str(row.get("cell_type", "")).strip()
        if tuning not in HOOK_TUNINGS:
            continue
        if not _truthy(row.get("valid")):
            continue
        if str(row.get("classification_system", "")).strip() != "T1L":
            continue
        root_id = _normalise_id(row.get("pt_root_id"))
        if not root_id:
            raise ValueError("Lee hook row is missing pt_root_id")
        rows.append({"fanc_root_id": root_id, "tuning": tuning})
    rows.sort(key=lambda row: (row["tuning"], row["fanc_root_id"]))
    ids = [row["fanc_root_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Lee hook pt_root_id values are not unique")
    return rows


def _index_meta(meta_rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in meta_rows:
        for field in ("banc_888_id", "root_888"):
            key = _normalise_id(row.get(field))
            if key:
                index[key] = row
    return index


def _query_root_888(row: dict[str, Any]) -> str:
    for field in ("root_888", "pt_root_id", "query_root_id"):
        value = _normalise_id(row.get(field))
        if value:
            return value
    return ""


def build_crosswalk(
    lee_rows: list[dict[str, str]],
    nblast_rows: Iterable[dict[str, Any]],
    meta_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    lee_by_id = {row["fanc_root_id"]: row["tuning"] for row in lee_rows}
    meta_index = _index_meta(meta_rows)
    exact_pairs: list[dict[str, Any]] = []

    for row in nblast_rows:
        match_id = _normalise_id(row.get("match_id"))
        if match_id not in lee_by_id or not _truthy(row.get("validation")):
            continue
        root_888 = _query_root_888(row)
        meta = meta_index.get(root_888)
        exact_pairs.append(
            {
                "fanc_root_id": match_id,
                "lee_tuning": lee_by_id[match_id],
                "banc_root_888": root_888,
                "nblast_score": round(float(row.get("score") or 0.0), 12),
                "validation": True,
                "banc_meta_found": meta is not None,
                "banc_root_626": _normalise_id(meta.get("root_626")) if meta else "",
                "banc_cell_type": str(meta.get("cell_type") or "") if meta else "",
                "banc_fanc_cell_type": str(meta.get("fanc_cell_type") or "") if meta else "",
                "banc_fanc_match": str(meta.get("fanc_match") or "") if meta else "",
                "banc_fanc_nblast_match": _normalise_id(meta.get("fanc_nblast_match")) if meta else "",
                "banc_malecns_cell_type": str(meta.get("malecns_cell_type") or "") if meta else "",
                "banc_manc_cell_type": str(meta.get("manc_cell_type") or "") if meta else "",
            }
        )

    exact_pairs.sort(key=lambda row: (row["lee_tuning"], row["fanc_root_id"], row["banc_root_888"]))

    type_level_rows: list[dict[str, Any]] = []
    for meta in meta_rows:
        cell_type = str(meta.get("cell_type") or "")
        fanc_cell_type = str(meta.get("fanc_cell_type") or "")
        if cell_type not in SYSTEMATIC_TYPES or fanc_cell_type not in HOOK_TUNINGS:
            continue
        type_level_rows.append(
            {
                "banc_root_888": _normalise_id(meta.get("banc_888_id") or meta.get("root_888")),
                "banc_root_626": _normalise_id(meta.get("root_626")),
                "banc_cell_type": cell_type,
                "fanc_cell_type": fanc_cell_type,
                "fanc_match": str(meta.get("fanc_match") or ""),
                "fanc_nblast_match": _normalise_id(meta.get("fanc_nblast_match")),
                "malecns_cell_type": str(meta.get("malecns_cell_type") or ""),
                "manc_cell_type": str(meta.get("manc_cell_type") or ""),
            }
        )
    type_level_rows.sort(key=lambda row: (row["banc_cell_type"], row["fanc_cell_type"], row["banc_root_888"]))

    pair_groups: dict[str, set[str]] = defaultdict(set)
    pair_ids: dict[str, set[str]] = defaultdict(set)
    pair_conflicts: list[dict[str, Any]] = []
    by_fanc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in exact_pairs:
        by_fanc[row["fanc_root_id"]].append(row)
        if row["banc_cell_type"] in SYSTEMATIC_TYPES:
            pair_groups[row["lee_tuning"]].add(row["banc_cell_type"])
            pair_ids[row["lee_tuning"]].add(row["fanc_root_id"])
    for fanc_id, rows in sorted(by_fanc.items()):
        roots = {row["banc_root_888"] for row in rows}
        types = {row["banc_cell_type"] for row in rows if row["banc_cell_type"]}
        if len(roots) != 1 or len(types) > 1:
            pair_conflicts.append({"fanc_root_id": fanc_id, "banc_roots": sorted(roots), "cell_types": sorted(types)})

    type_groups: dict[str, set[str]] = defaultdict(set)
    for row in type_level_rows:
        type_groups[row["banc_cell_type"]].add(row["fanc_cell_type"])

    tuning_to_type = {key: sorted(value) for key, value in sorted(pair_groups.items())}
    type_to_tuning = {key: sorted(value) for key, value in sorted(type_groups.items())}
    lee_ids = {row["fanc_root_id"] for row in lee_rows}
    validated_ids = set(by_fanc)

    exact_bijection = (
        tuning_to_type.get("hook_flx") is not None
        and tuning_to_type.get("hook_ext") is not None
        and len(tuning_to_type["hook_flx"]) == 1
        and len(tuning_to_type["hook_ext"]) == 1
        and tuning_to_type["hook_flx"][0] != tuning_to_type["hook_ext"][0]
    )
    type_level_bijection = (
        all(len(type_to_tuning.get(cell_type, [])) == 1 for cell_type in SYSTEMATIC_TYPES)
        and {type_to_tuning[cell_type][0] for cell_type in SYSTEMATIC_TYPES} == set(HOOK_TUNINGS)
    )
    exact_and_type_level_agree = False
    if exact_bijection and type_level_bijection:
        exact_map = {tuning: types[0] for tuning, types in tuning_to_type.items() if tuning in HOOK_TUNINGS}
        type_map = {tunings[0]: cell_type for cell_type, tunings in type_to_tuning.items() if cell_type in SYSTEMATIC_TYPES}
        exact_and_type_level_agree = exact_map == type_map

    evidence_gates = {
        "all_22_lee_hook_ids_have_exact_expert_validated_banc_match": validated_ids == lee_ids,
        "each_lee_hook_id_has_exactly_one_validated_banc_root": len(pair_conflicts) == 0 and all(len(rows) == 1 for rows in by_fanc.values()),
        "all_exact_matches_have_banc_metadata": all(row["banc_meta_found"] for row in exact_pairs),
        "all_exact_matches_resolve_to_snpp39_or_snpp41": bool(exact_pairs) and all(row["banc_cell_type"] in SYSTEMATIC_TYPES for row in exact_pairs),
        "exact_validated_pairs_form_tuning_to_type_bijection": exact_bijection,
        "banc_curated_fanc_cell_type_forms_type_to_tuning_bijection": type_level_bijection,
        "exact_pairs_and_curated_type_level_mapping_agree": exact_and_type_level_agree,
    }
    candidate_resolved = all(evidence_gates.values())

    candidate_mapping: dict[str, str] = {}
    if candidate_resolved:
        candidate_mapping = {tuning: tuning_to_type[tuning][0] for tuning in HOOK_TUNINGS}

    return {
        "lee_hook_count": len(lee_rows),
        "lee_hook_counts_by_tuning": {
            tuning: sum(1 for row in lee_rows if row["tuning"] == tuning) for tuning in HOOK_TUNINGS
        },
        "expert_validated_pair_count": len(exact_pairs),
        "expert_validated_unique_fanc_ids": len(validated_ids),
        "unmatched_lee_hook_ids": sorted(lee_ids - validated_ids),
        "exact_pair_conflicts": pair_conflicts,
        "exact_pairs": exact_pairs,
        "tuning_to_systematic_types_from_exact_pairs": tuning_to_type,
        "banc_type_level_rows": type_level_rows,
        "systematic_type_to_fanc_tuning_from_curated_meta": type_to_tuning,
        "evidence_gates": evidence_gates,
        "candidate_direction_polarity_resolved": candidate_resolved,
        "candidate_mapping": candidate_mapping,
    }


def build_report(
    *,
    lee_csv_text: str,
    nblast_rows: list[dict[str, Any]],
    meta_rows: list[dict[str, Any]],
    source_receipts: dict[str, Any],
    expected_receipt_sha256: str | None = EXPECTED_RECEIPT_SHA256,
) -> dict[str, Any]:
    lee_rows = parse_lee_hook_rows(lee_csv_text)
    crosswalk = build_crosswalk(lee_rows, nblast_rows, meta_rows)
    counts_ok = crosswalk["lee_hook_counts_by_tuning"] == LEE_EXPECTED_COUNTS
    source_gates = {
        "lee_commit_is_pinned": source_receipts.get("lee_commit") == LEE_COMMIT,
        "lee_table_blob_is_pinned": source_receipts.get("lee_table_blob_sha1") == LEE_TABLE_BLOB_SHA1,
        "lee_hook_counts_are_13_flexion_9_extension": counts_ok,
        "banc_project_commit_is_pinned": source_receipts.get("banc_project_commit") == BANC_PROJECT_COMMIT,
        "banc_meta_md5_matches_documented_snapshot": source_receipts.get("banc_meta_md5") == BANC_META_EXPECTED_MD5,
        "banc_meta_size_matches_documented_snapshot": source_receipts.get("banc_meta_size") == BANC_META_EXPECTED_SIZE,
        "banc_fanc_nblast_size_matches_documented_snapshot": source_receipts.get("banc_fanc_nblast_size") == BANC_FANC_NBLAST_EXPECTED_SIZE,
        "stimulation_remains_disabled": True,
        "current_calibration_remains_blocked": True,
    }
    canonical_receipt = {
        "schema": SCHEMA,
        "source_receipts": source_receipts,
        "crosswalk": crosswalk,
    }
    receipt_sha = _sha256_json(canonical_receipt)
    structural_pass = all(source_gates.values())
    frozen = expected_receipt_sha256 is not None
    receipt_matches = frozen and receipt_sha == expected_receipt_sha256
    gates = {
        **source_gates,
        "receipt_frozen": frozen,
        "receipt_matches": bool(receipt_matches),
    }
    passed = all(gates.values())
    if passed:
        status = STATUS_REVIEW
    elif structural_pass and not frozen:
        status = STATUS_DISCOVERY
    else:
        status = STATUS_FAIL

    resolved = bool(passed and crosswalk["candidate_direction_polarity_resolved"])
    mapping = crosswalk["candidate_mapping"] if resolved else {}
    return {
        "schema": SCHEMA,
        "status": status,
        "passed": passed,
        "receipt_sha256": receipt_sha,
        "expected_receipt_sha256": expected_receipt_sha256,
        "source_receipts": source_receipts,
        "crosswalk": crosswalk,
        "systematic_type_direction_polarity_resolved": resolved,
        "resolved_tuning_to_systematic_type": mapping,
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "gates": gates,
        "interpretation": (
            "This audit attempts an exact Lee/FANC hook-tuning -> expert-reviewed BANC/FANC match -> "
            "BANC source-of-truth systematic-type crosswalk. Discovery mode never resolves polarity. "
            "A frozen receipt may resolve polarity only if every predeclared evidence gate passes; "
            "even then proprioceptive current remains unauthorized pending a separate calibration."
        ),
    }


def discover() -> dict[str, Any]:
    try:
        import pyarrow.feather as feather
    except ImportError as exc:  # pragma: no cover - external workflow dependency
        raise RuntimeError("pyarrow is required for the external polarity crosswalk discovery") from exc

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        lee_path = root / "feco_annotation_table.csv"
        meta_path = root / "banc_888_meta.feather"
        nblast_path = root / "banc_fanc_1116_nblast.feather"
        _download(LEE_TABLE_URL, lee_path)
        _download(BANC_META_URL, meta_path)
        _download(BANC_FANC_NBLAST_URL, nblast_path)

        meta_columns = [
            "banc_888_id", "root_626", "root_850", "root_888", "cell_type",
            "fanc_cell_type", "fanc_match", "fanc_nblast_match", "malecns_cell_type",
            "manc_cell_type", "super_class", "cell_class", "cell_sub_class", "flow",
            "body_part_sensory", "peripheral_target_type", "cell_function",
        ]
        nblast_columns = [
            "pt_root_id", "query_root_id", "match_id", "score", "root_626", "root_850",
            "root_888", "validation",
        ]
        meta_rows = feather.read_table(meta_path, columns=meta_columns).to_pylist()
        nblast_rows = feather.read_table(nblast_path, columns=nblast_columns).to_pylist()
        source_receipts = {
            "lee_repository": LEE_REPOSITORY,
            "lee_commit": LEE_COMMIT,
            "lee_table_blob_sha1": LEE_TABLE_BLOB_SHA1,
            "lee_table_sha256": _file_digest(lee_path, "sha256"),
            "lee_table_size": lee_path.stat().st_size,
            "banc_project_repository": BANC_PROJECT_REPOSITORY,
            "banc_project_commit": BANC_PROJECT_COMMIT,
            "banc_meta_url": BANC_META_URL,
            "banc_meta_md5": _file_digest(meta_path, "md5"),
            "banc_meta_sha256": _file_digest(meta_path, "sha256"),
            "banc_meta_size": meta_path.stat().st_size,
            "banc_fanc_nblast_url": BANC_FANC_NBLAST_URL,
            "banc_fanc_nblast_sha256": _file_digest(nblast_path, "sha256"),
            "banc_fanc_nblast_size": nblast_path.stat().st_size,
        }
        return build_report(
            lee_csv_text=lee_path.read_text(),
            nblast_rows=nblast_rows,
            meta_rows=meta_rows,
            source_receipts=source_receipts,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = discover()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
