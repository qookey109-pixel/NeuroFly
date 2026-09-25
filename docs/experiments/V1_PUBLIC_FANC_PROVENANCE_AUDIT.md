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

## Acceptance boundary

Only direct provenance counts here. SWC/mesh geometric resemblance is not used
as evidence and cannot satisfy the curated identity gate.

If no direct root-bearing public object exists, this public-only route is
closed and authenticated `cell_ids_v2` remains the authoritative next step.

## Locks

All polarity/calibration/runtime promotion locks remain closed.
