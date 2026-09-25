# V1 FeCO Dallmann FANC v840 audit

## Independent source

Dallmann et al. (2025), *Selective presynaptic inhibition of leg proprioception in behaving Drosophila*, reports FANC analyses on materialization v840. The accompanying public repository `chrisjdallmann/feco-inhibition` contains the figure-reproduction code.

## Reproducible finding

The public notebook `code/fanc_feco_connectivity.ipynb` explicitly queries:

- datastack: `fanc_production_mar2021`
- materialization: `840`
- annotation table: `feco_axons_v0`
- cell types: `claw_flx`, `claw_ext`, `hook_flx`, `hook_ext`

It then obtains FeCO connectome identities directly from `df_feco.pt_root_id` and associates each root with the annotation-table `id` and `cell_type`.

This independently confirms that FANC v840 contains explicit root-level `hook_flx` annotations; hook-flexion is not merely inferred from morphology in that analysis.

## Boundary

The public notebook contains the query procedure but not the returned `feco_axons_v0` rows. Reproducing the actual `hook_flx -> pt_root_id` list requires authenticated CAVE access. The companion Dryad inventory contains calcium/behaviour/RNA-seq and selected connectome exports, but its documented public files do not expose the full `feco_axons_v0` table.

Therefore this route strengthens the FANC side of the bridge but does **not** by itself map the frozen MaleCNS/BANC SNpp41 target to a specific FANC `hook_flx` root.

## Gate state

- independent FANC hook-flexion annotation procedure: confirmed
- explicit FANC hook_flx root list from this public route: not recovered
- SNpp41 -> FANC hook_flx cell-level mapping: unresolved
- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked

## Next route

Use the now-fixed FANC v840 `feco_axons_v0` namespace as the target side of an independent cross-dataset bridge. Do not reopen candidate 20201 or the exhausted public raw-NBLAST route.
