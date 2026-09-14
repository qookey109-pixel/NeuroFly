# V0.11 SNpp39 / SNpp41 Polarity Crosswalk Audit

Status: discovery-first, read-only biological identity audit. No proprioceptive current, stimulation, or runtime transduction is authorized here.

## Goal

Resolve, if the public evidence is exact enough, the remaining systematic-type polarity question:

- which of `SNpp39` / `SNpp41` corresponds to FeCO `hook_flx`;
- which corresponds to FeCO `hook_ext`.

The audit deliberately does **not** infer sensory polarity from motor-circuit effects, target morphology, or an NBLAST score alone.

## Frozen source chain

### Lee et al. FANC FeCO functional annotations

Repository: `sagrawal/Lee_2024`

Pinned commit:

`4328b1d5549749f1014c4d73cccc0c5241d98ae4`

Pinned annotation-table blob SHA-1:

`3346a13fa31af8779eb39b277c443a252ff86115`

File:

`synapse_tables/feco_annotation_table.csv`

Only valid `T1L` rows whose `cell_type` is exactly `hook_flx` or `hook_ext` are eligible. The pinned table is expected to contain exactly:

- `hook_flx`: 13
- `hook_ext`: 9

Every eligible row carries an exact FANC `pt_root_id`.

### BANC cross-dataset matching and source-of-truth metadata

Repository/documentation authority: `htem/BANC-project`

Pinned project commit:

`e31a2e26b9937dca72e5ca1c1960df6454d76114`

Public BANC v888 metadata:

`gs://lee-lab_brain-and-nerve-cord-fly-connectome/compiled_data/banc_888/banc_888_meta.feather`

Documented MD5:

`8c8babff28b21c57ecc999e664560ef5`

Documented byte size:

`51450978`

Public BANC↔FANC v1116 NBLAST table:

`gs://lee-lab_brain-and-nerve-cord-fly-connectome/nblast/banc_fanc_1116_nblast.feather`

Documented byte size:

`93624386`

The official NBLAST schema includes exact FANC `match_id`, BANC query identifiers, normalized `score`, v626/v850/v888 roots, and an expert-review `validation` flag. This audit uses only `validation == TRUE` rows for the exact-pair bridge.

The BANC metadata `cell_type` column is treated as source-of-truth systematic identity. `fanc_cell_type`, `fanc_match`, and `fanc_nblast_match` are retained as an independent curated type-level cross-check.

## Predeclared resolution gates

A frozen receipt may set `systematic_type_direction_polarity_resolved=true` only if **all** of the following are true:

1. all 22 pinned Lee hook IDs have an exact expert-validated BANC match;
2. each Lee hook ID has exactly one validated BANC root;
3. every exact pair resolves to BANC metadata;
4. every exact pair's BANC source-of-truth `cell_type` is `SNpp39` or `SNpp41`;
5. the exact pairs form a one-to-one tuning→systematic-type mapping (`hook_flx` and `hook_ext` map to different systematic types with no mixing);
6. BANC curated `fanc_cell_type` rows for `SNpp39` and `SNpp41` independently form the inverse one-to-one mapping;
7. the exact-pair mapping and curated type-level mapping agree exactly.

These criteria are frozen **before** inspecting the real crosswalk output. Missing coverage or any mixed/conflicting assignment remains unresolved; the gate must not be weakened after discovery.

## Discovery-first policy

`EXPECTED_RECEIPT_SHA256` starts unset. The first external run must publish the exact source hashes, exact validated pairs, unmatched IDs, conflicts, type-level rows, and candidate mapping, then return `DISCOVERY_REQUIRED` if source-integrity gates pass.

Discovery mode never resolves polarity even if the observed mapping is clean.

Only a later commit may freeze the exact receipt. A reproduced frozen receipt can change the polarity status only if every predeclared evidence gate is true.

## Hard locks

Regardless of polarity result:

- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

A resolved polarity crosswalk would authorize only a later **separate, predeclared, frozen-weight MaleCNS current calibration**. It would not itself authorize neural stimulation.
