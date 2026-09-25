# V1 FeCO authenticated stable-ID extraction

## Why this exists

The remaining FeCO identity gate is now a bounded data join, not an open-ended morphology search.

Input:

`data/research/feco/fanc_v840_t1l_hook_flx_roots.csv`

contains the 13 frozen FANC v840 T1L `hook_flx` roots.

Required output:

`pt_root_id -> stable FANC cell ID`

for all 13 roots.

## ID-column equivalence

The public FANC `new_cell()` implementation uses `cell_ids_v2` and, when allocating a new stable cell ID, stages the same `upload_id` into both:

- the annotation row `id`
- the table's configured cell-ID field, currently `user_id`

This explains why FANC lookup helpers use `user_id` while BANCpipeline materializes `cell_id = id`.

The extractor records both columns and an `id_equals_user_id` flag instead of silently assuming equivalence.

## Reproducible extractor

`scripts/research/export_fanc_hook_flx_stable_ids.py`

performs one authenticated, read-only query:

- datastack: `fanc_production_mar2021`
- materialization: `840`
- table: `cell_ids_v2`
- filter: the 13 frozen `pt_root_id` values

It writes:

`data/research/feco/fanc_v840_t1l_hook_flx_stable_ids.csv`

The script:

- never accepts a token as a command-line argument
- never writes credentials
- fails on duplicate root mappings
- reports partial recovery as a non-zero exit
- preserves both `id` and `user_id` for audit

## Acceptance boundary

A successful 13/13 export closes only the FANC root-to-stable-ID subproblem.

It does not by itself prove:

`SNpp41 -> one specific FANC hook_flx cell`

The exported stable IDs must still be joined against accepted BANC/FANC match evidence, and the resulting individual-cell bridge must satisfy the frozen curation rule before exact polarity, Current Calibration, or Runtime stimulation can be unlocked.

## Gate state

Until that join is completed and accepted:

- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked
