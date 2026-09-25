# V1 public FANC provenance audit

## Purpose

Test the last public-only namespace route without treating morphology similarity
as identity.

The BANC pipeline writes transformed FANC meshes locally as `<root_id>.obj`,
then uploads those meshes to the public Neuroglancer layer using stable FANC
`cell_id` as `mesh_id`.

If a public root-named OBJ, root-bearing manifest, or root property survives
publication, it can provide exact namespace provenance:

`FANC root_id -> stable FANC cell_id`

without CAVE authentication.

## Audit

The probe:

- exhaustively lists public `compiled_data/fanc_1116/` and `nblast/`;
- searches all 13 frozen `hook_flx` roots in public object names;
- distinguishes expected root-named SWCs from any non-SWC root-bearing object;
- probes likely root-named OBJ paths directly;
- probes root-named entries in the public FANC mesh layer;
- inspects public layer and segment-properties JSON for any root property.

## Observed result

GitHub Actions run `36089073238` completed successfully and produced artifact
`public-fanc-provenance-audit` (artifact id `10844724488`).

Public inventory:

- `compiled_data/fanc_1116/`: **21,865 objects**, exhaustively enumerated in
  22 paginated requests;
- `nblast/`: **14 objects**, exhaustively enumerated;
- all 13 frozen hook-flexion roots appear publicly only as
  `fanc_banc_space_swc/<root_id>.swc`;
- roots with any non-SWC public object: **0/13**;
- public root-named OBJ files found: **0**;
- public root-named mesh entries found: **0**;
- all tested likely root-named OBJ paths returned 404.

The public FANC layer metadata is readable, but it contains no root property.
The public `segment_properties` object contains 21,952 stable IDs and only
`label` / `tags` properties; it does not expose `root_id` or
`pt_root_id`.

Therefore:

`exact_public_provenance_bridge_found = false`

The public root-named SWCs are useful morphology products, but they cannot invert
the separately published stable-cell-ID mesh namespace.

## Acceptance boundary

Only direct provenance counts here. SWC/mesh geometric resemblance is not used
as evidence and cannot satisfy the curated identity gate.

This closes the remaining public-only exact-provenance route. Reconstructing a
root-to-cell-ID relation by geometric similarity would violate the frozen
identity acceptance boundary and is therefore not promoted.

## Next authoritative route

The remaining authoritative route is the read-only authenticated query already
implemented in:

`scripts/research/export_fanc_hook_flx_stable_ids.py`

Target:

- datastack: `fanc_production_mar2021`
- materialization: `840`
- table: `cell_ids_v2`
- filter: the 13 frozen `hook_flx` roots

Once the 13 stable IDs are recovered, they can be joined directly to BANC FANC
`match_id` products. No further anonymous/public namespace-search route should
be reopened unless a new authoritative dataset is published.

## Locks

- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked
