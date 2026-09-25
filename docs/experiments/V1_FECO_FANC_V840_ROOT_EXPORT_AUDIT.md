# V1 FeCO FANC v840 root export audit

## Question

Can the public Dallmann FeCO release close the remaining bridge by exposing the actual FANC v840 `feco_axons_v0` rows for `hook_flx`?

Required endpoint:

`MaleCNS 911942 / SNpp41 -> specific FANC pt_root_id -> hook_flx`

## Reproducible public-source audit

The Dallmann public repository was inspected recursively.

The figure code in `code/fanc_feco_connectivity.ipynb` obtains FeCO identities at runtime with:

- datastack `fanc_production_mar2021`
- materialization version `840`
- table `feco_axons_v0`
- requested types `claw_flx`, `claw_ext`, `hook_flx`, `hook_ext`
- root identifier column `pt_root_id`

The repository tree does not contain a checked-in export of `feco_axons_v0` or a static table of the returned hook-flexion roots.

The documented companion-data inventory lists calcium/behaviour parquet files, RNA-seq data, selected FANC descending-neuron information, and MANC simulation/connectivity products. It does not document a `feco_axons_v0` export containing the required `hook_flx -> pt_root_id` rows.

Therefore the public repository is sufficient to reproduce the query **given authenticated CAVE access**, but not sufficient by itself to recover the returned rows offline.

## Result

- FANC v840 hook_flx query definition: confirmed
- public static feco_axons_v0 export in audited release: not found
- public hook_flx pt_root_id row set from this route: not recovered
- SNpp41 -> specific FANC hook_flx root: unresolved

This route is now marked exhausted **as a static-public-export route**. It should only be reopened if a new public table/export appears or authenticated CAVE materialization becomes available.

## Governance

No type-level, morphology-level, or circuit-level evidence is promoted to exact cell identity.

- bridge_is_type_exclusive: false
- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked

## Next evidence route

Move to an independent cross-dataset mapping source that can explicitly join BANC/MaleCNS identity to a FANC root. Do not repeat the public Dallmann static-export search and do not reopen retired candidate 20201.
