from __future__ import annotations

from copy import deepcopy

from neurofly.proprioception_polarity_crosswalk_audit import (
    BANC_FANC_NBLAST_EXPECTED_SIZE,
    BANC_META_EXPECTED_MD5,
    BANC_META_EXPECTED_SIZE,
    BANC_PROJECT_COMMIT,
    LEE_COMMIT,
    LEE_TABLE_BLOB_SHA1,
    build_crosswalk,
    build_report,
    parse_lee_hook_rows,
)


def _lee_csv() -> str:
    lines = ["valid,classification_system,cell_type,pt_root_id"]
    for index in range(13):
        lines.append(f"t,T1L,hook_flx,{1000 + index}")
    for index in range(9):
        lines.append(f"t,T1L,hook_ext,{2000 + index}")
    return "\n".join(lines) + "\n"


def _clean_rows():
    nblast = []
    meta = []
    counter = 3000
    for tuning, fanc_ids, cell_type in (
        ("hook_flx", range(1000, 1013), "SNpp39"),
        ("hook_ext", range(2000, 2009), "SNpp41"),
    ):
        for fanc_id in fanc_ids:
            root = str(counter)
            counter += 1
            nblast.append(
                {
                    "match_id": str(fanc_id),
                    "validation": True,
                    "root_888": root,
                    "score": 0.8,
                }
            )
            meta.append(
                {
                    "banc_888_id": root,
                    "root_888": root,
                    "root_626": str(int(root) + 10000),
                    "cell_type": cell_type,
                    "fanc_cell_type": tuning,
                    "fanc_match": "TRUE",
                    "fanc_nblast_match": str(fanc_id),
                    "malecns_cell_type": cell_type,
                    "manc_cell_type": cell_type,
                }
            )
    return nblast, meta


def _source_receipts():
    return {
        "lee_commit": LEE_COMMIT,
        "lee_table_blob_sha1": LEE_TABLE_BLOB_SHA1,
        "banc_project_commit": BANC_PROJECT_COMMIT,
        "banc_meta_md5": BANC_META_EXPECTED_MD5,
        "banc_meta_size": BANC_META_EXPECTED_SIZE,
        "banc_fanc_nblast_size": BANC_FANC_NBLAST_EXPECTED_SIZE,
    }


def test_lee_parser_requires_exact_expected_hook_population_shape():
    rows = parse_lee_hook_rows(_lee_csv())
    assert len(rows) == 22
    assert sum(row["tuning"] == "hook_flx" for row in rows) == 13
    assert sum(row["tuning"] == "hook_ext" for row in rows) == 9


def test_clean_exact_and_curated_crosswalk_is_candidate_resolved():
    lee = parse_lee_hook_rows(_lee_csv())
    nblast, meta = _clean_rows()
    result = build_crosswalk(lee, nblast, meta)
    assert result["candidate_direction_polarity_resolved"] is True
    assert result["candidate_mapping"] == {"hook_flx": "SNpp39", "hook_ext": "SNpp41"}
    assert result["unmatched_lee_hook_ids"] == []


def test_discovery_never_resolves_polarity_until_receipt_is_frozen():
    nblast, meta = _clean_rows()
    report = build_report(
        lee_csv_text=_lee_csv(),
        nblast_rows=nblast,
        meta_rows=meta,
        source_receipts=_source_receipts(),
    )
    assert report["status"] == "DISCOVERY_REQUIRED"
    assert report["passed"] is False
    assert report["crosswalk"]["candidate_direction_polarity_resolved"] is True
    assert report["systematic_type_direction_polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_clean_receipt_can_resolve_polarity_but_not_current():
    nblast, meta = _clean_rows()
    discovery = build_report(
        lee_csv_text=_lee_csv(),
        nblast_rows=nblast,
        meta_rows=meta,
        source_receipts=_source_receipts(),
    )
    verified = build_report(
        lee_csv_text=_lee_csv(),
        nblast_rows=nblast,
        meta_rows=meta,
        source_receipts=_source_receipts(),
        expected_receipt_sha256=discovery["receipt_sha256"],
    )
    assert verified["passed"] is True
    assert verified["status"] == "REVIEW_REQUIRED"
    assert verified["systematic_type_direction_polarity_resolved"] is True
    assert verified["resolved_tuning_to_systematic_type"] == {
        "hook_flx": "SNpp39",
        "hook_ext": "SNpp41",
    }
    assert verified["current_calibration_authorized"] is False
    assert verified["stimulation_enabled"] is False


def test_missing_one_expert_validated_hook_keeps_candidate_unresolved():
    lee = parse_lee_hook_rows(_lee_csv())
    nblast, meta = _clean_rows()
    result = build_crosswalk(lee, nblast[:-1], meta)
    assert result["candidate_direction_polarity_resolved"] is False
    assert result["evidence_gates"]["all_22_lee_hook_ids_have_exact_expert_validated_banc_match"] is False


def test_mixed_systematic_type_within_one_tuning_keeps_candidate_unresolved():
    lee = parse_lee_hook_rows(_lee_csv())
    nblast, meta = _clean_rows()
    mutated = deepcopy(meta)
    mutated[0]["cell_type"] = "SNpp41"
    result = build_crosswalk(lee, nblast, mutated)
    assert result["candidate_direction_polarity_resolved"] is False
    assert result["evidence_gates"]["exact_validated_pairs_form_tuning_to_type_bijection"] is False


def test_type_level_crosswalk_must_agree_with_exact_pairs():
    lee = parse_lee_hook_rows(_lee_csv())
    nblast, meta = _clean_rows()
    mutated = deepcopy(meta)
    for row in mutated:
        if row["cell_type"] == "SNpp39":
            row["fanc_cell_type"] = "hook_ext"
        elif row["cell_type"] == "SNpp41":
            row["fanc_cell_type"] = "hook_flx"
    result = build_crosswalk(lee, nblast, mutated)
    assert result["candidate_direction_polarity_resolved"] is False
    assert result["evidence_gates"]["exact_pairs_and_curated_type_level_mapping_agree"] is False
