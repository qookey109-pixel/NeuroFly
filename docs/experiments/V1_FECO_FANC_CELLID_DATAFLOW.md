# V1 FeCO FANC cell-ID dataflow audit

## Purpose

This stage resolves the identifier ambiguity that remained after recovering the 13 explicit FANC v840 T1L `hook_flx` roots.

The remaining bridge is not a morphology-search problem. It is an identifier join:

`FANC hook_flx pt_root_id -> stable FANC cell_id -> BANC/MaleCNS cross-dataset match`

## FANC stable-ID source

The public `htem/FANC_auto_recon` lookup implementation defines `cell_ids_v2` as the default stable-cell-ID source and provides a direct `cellid_from_segid()` lookup:

- input: FANC `pt_root_id`
- table: `cell_ids_v2`
- output: stable cell ID

This independently confirms that root-to-stable-ID is a first-class FANC identity operation.

## BANC pipeline materialization

The public `htem/bancpipeline/fanc/fanc-meta.R` pipeline queries `cell_ids_v2`, reduces it to:

- `cell_id = id`
- `pt_root_id`
- `root_position`

and joins it into `fanc_meta.csv` by `pt_root_id`.

Therefore `fanc_meta.csv` is the exact root-to-stable-ID bridge artifact needed for the 13 recovered hook-flexion roots.

## Exact FANC NBLAST identifier flow

The public BANC/FANC NBLAST code removes the remaining ambiguity.

### Raw per-query NBLAST

`banc-fanc-nblast.R` runs against FANC root IDs and writes rows carrying:

- `fanc_id` / `fanc_match`: FANC root ID
- `cell_id`: stable FANC cell ID joined from `fanc_meta.csv`
- `cell_type`
- NBLAST score

A raw per-query result for the frozen BANC SNpp41 root would therefore be sufficient to relate a candidate stable FANC ID back to its FANC root.

### Compiled BANC/FANC NBLAST

`banc-nblast-compile.R` deliberately converts the FANC result into:

`match_id = cell_id`

Thus the public compiled BANC/FANC `match_id` namespace is the **stable FANC cell-ID namespace**, not the FANC root-ID namespace.

### Reviewed FANC matches

For manually reviewed FANC match PNGs, the pipeline initially parses a FANC root ID from the hit filename, then converts it through:

`fc.meta$cell_id[match(fanc_root_id, fc.meta$root_id)]`

before emitting reviewed `match_id`.

So both compiled NBLAST and reviewed-match products converge on stable FANC `cell_id`.

## Consequence for candidate 20201

The previously observed `match_id = 20201` is therefore a stable FANC cell ID.

This semantic clarification does **not** promote candidate 20201. Prior evidence remains insufficient: no accepted reviewed match or root-level identity bridge for SNpp41 has been recovered, and the prior public compiled candidate was not adequate under the frozen acceptance rule.

Do not reopen 20201 as an identity merely because its namespace is now known.

## Public segment-properties boundary

The public FANC Neuroglancer segment-properties publisher uses:

`id_col = cell_id`

but serializes only the ID plus label/tags. `root_id` is not included as a property.

Therefore that public layer cannot, by itself, invert one of the 13 hook-flexion roots into a stable cell ID.

## Current exact endpoint

Known:

`MaleCNS 911942 -> SNpp41`

`BANC 720575941508169089 -> SNpp41`

`FANC -> 13 explicit T1L hook_flx roots`

`BANC FANC match_id -> stable FANC cell_id`

Still required:

`13 hook_flx roots -> cell_ids_v2/fanc_meta.csv -> stable cell_id -> accepted BANC SNpp41 identity`

The search space is now fully specified and bounded.

## Gate state

- FANC hook_flx root enumeration: resolved
- FANC match-ID namespace: resolved
- root-to-cell-ID mechanism: resolved
- actual stable cell IDs for the 13 frozen roots: not yet recovered
- SNpp41 -> specific FANC hook_flx root: unresolved
- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked

## Next route

Recover only the 13 root-to-`cell_id` rows from an authenticated `cell_ids_v2` query, a public `fanc_meta.csv` export, or an equivalent authoritative snapshot. Then join those stable IDs directly against BANC FANC match products.

Do not return to unrestricted morphology search, the exhausted public raw-object namespace, or candidate 20201 without new accepted evidence.
