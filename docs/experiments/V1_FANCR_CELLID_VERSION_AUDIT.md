# V1 official fancr cell-ID version audit

## Goal

Resolve the remaining FANC namespace question as narrowly as possible:

`FANC cell_id 20201 -> exact FANC root_id`

and test whether that root is one of the five exact `hook_flx` roots frozen by
PR #124.

## Why this route is different from PR #126

PR #126 tested hand-built anonymous CAVE requests at FANC v1.116 and documented
the Google OAuth/authentication boundary.

This audit additionally pins the official `flyconnectome/fancr`
implementation and follows its exact semantics:

- `fanc_segid_from_cellid()` queries a `cell_ids*` table by `id`;
- `fanc_cellid_from_segid()` queries the same table by `pt_root_id`;
- both support an explicit materialization `version`;
- `fanc_cellid_table()` deliberately chooses the newest table whose name
  contains `cell_ids`.

Pinned fancr commit:

`7b3d429729627d83dad9387f54294272640e87f9`

## Version rationale

Two FANC snapshots are tested:

- **840** — pinned by Dallmann et al. 2025 for FeCO analysis using
  `feco_axons_v0`;
- **1116** — the FANC snapshot used by the public BANC↔FANC NBLAST product that
  reports candidate `match_id=20201`.

The fancr documentation treats cell IDs as persistent identifiers intended to
survive most segmentation edits, while root IDs are edit-state-specific.

## Independent directional anchor

The audit also re-verifies the pinned Lee 2024 static
`synapse_tables/feco_annotation_table.csv`.

The five frozen PR #124 cells must remain exact:

- T1L;
- `hook_flx`;
- the same five root IDs;
- the same five supervoxel IDs.

## Decision rule

A namespace bridge is positive only when an official `cell_ids*` response
contains exact integer equality:

`id == 20201`

and

`pt_root_id IN {five frozen hook_flx roots}`.

Both forward and reverse queries are run.

HTTP 401/403 or HTTP-200 Google login HTML is an authentication boundary, not a
negative scientific result.

## Governance

Even a positive namespace mapping would **not** validate the BANC↔FANC NBLAST
candidate because the published BANC row still has `validation=false`.

Therefore this audit does not automatically set:

- `curated_fanc_to_manc_snpp_bridge_found=true`
- `exact_polarity_verified=true`
- calibration authorization
- runtime stimulation authorization
- privileged-state bypass authorization
