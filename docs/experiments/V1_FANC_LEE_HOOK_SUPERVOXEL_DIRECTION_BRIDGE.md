# V1 FANC–Lee hook supervoxel direction bridge audit

## Question

Can the five author-pinned Phelps/GridTape legacy FANC hook skeletons be linked
directly to Lee et al. T1L `hook_flx` / `hook_ext` annotations without CAVE
root access and without recomputing morphology?

## Pinned sources

Phelps/GridTape:

- repository: `htem/GridTape_VNC_paper`
- commit: `5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9`
- legacy CATMAID skeleton IDs: `25849, 25842, 25856, 24831, 25909`

Lee:

- repository: `sagrawal/Lee_2024`
- commit: `4328b1d5549749f1014c4d73cccc0c5241d98ae4`
- table: `synapse_tables/feco_annotation_table.csv`
- eligible rows: valid `T1L` rows whose `cell_type` is exactly
  `hook_flx` or `hook_ext`

## Exact bridge rule

For each legacy Phelps SWC:

1. read every SWC node;
2. convert FANC v3 voxel coordinates to FANC v4 using the same official
   transform-service path frozen in PR #123;
3. query the public FANC v4 point-to-supervoxel service;
4. form the set of non-zero supervoxel IDs traversed by the SWC;
5. compare that set against Lee's pinned hook annotation
   `pt_supervoxel_id` values.

A positive cell-level bridge exists **only** when the integer
`pt_supervoxel_id` is present in the mapped SWC supervoxel set.

The probe also re-queries Lee's stored `pt_position` values and requires the
public service to return the same pinned supervoxel before an anchor is eligible.

## Non-evidence

The following must not be promoted to identity:

- spatial proximity;
- same decimal ID in another namespace;
- inferred root membership;
- NBLAST or morphology rank;
- file order or JSON adjacency;
- BANC FANC candidate `20201`, because PR #121 froze its author validation as
  `false`.

## Relationship to the current SNpp41 chain

Merged PR #121 independently freezes:

`SNpp41 -> femoral hook proprioceptor -> MANC 97015 -> MaleCNS 911942`.

Merged PR #123 freezes the public infrastructure fact that the five legacy
Phelps hook SWCs can be transported into current FANC supervoxel space, while
anonymous current-root lookup remains authentication-blocked.

This audit is narrower. It asks whether exact segmentation IDs can add a
directional `hook_flx` / `hook_ext` label to those legacy EM cells.

Even a positive overlap does **not** by itself assert a curated FANC→MANC
identity or unlock runtime/calibration. A later evidence review must decide
whether a type-exclusive directional candidate set is sufficient for the
polarity gate.

## Hard locks

These remain false in this audit:

- `curated_r21d12_to_specific_fanc_em_identity_found`
- `curated_fanc_to_manc_snpp_bridge_found`
- `exact_polarity_verified`
- `current_calibration_authorized`
- `runtime_stimulation_authorized`
- `privileged_state_bypass_authorized`

## Observed result (2026-09-22)

The pinned Lee table exposed 22 valid T1L hook anchors whose stored
`pt_supervoxel_id` values were independently re-verified against the public FANC
point-to-supervoxel service.

All five pinned Phelps/GridTape legacy FANC hook skeletons produced an exact
integer supervoxel overlap with Lee `hook_flx` anchors:

- `24831 -> hook_flx`
- `25842 -> hook_flx`
- `25849 -> hook_flx`
- `25856 -> hook_flx`
- `25909 -> hook_flx`

Receipt summary:

- `legacy_cells_direction_resolved_by_exact_svid = 5`
- `all_five_resolved = true`
- `all_five_same_direction = true`
- `resolved_directions = ["hook_flx"]`
- `exact_svid_overlap_bridge_found = true`
- `type_exclusive_directional_candidate_set_found = true`
- `request_errors = []`

This is exact segmentation-ID evidence that the complete five-cell Phelps hook
candidate set used around the R21D12 EM–LM correspondence is flexion-directional.
It is stronger than morphology rank alone, but it is not a curated FANC->MANC
cell identity. Therefore the governance locks remain false in this PR.
