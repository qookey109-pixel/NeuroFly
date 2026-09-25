# V1 FeCO stable FANC cell-ID bridge audit

## Purpose

After recovering the 13 explicit FANC v840 T1L `hook_flx` roots, the remaining identity problem is narrower:

`FANC hook_flx pt_root_id -> stable FANC cell ID -> BANC/MaleCNS cross-dataset match`

BANC cross-dataset products use FANC match identifiers, while the Lee 2024 public FeCO export provides FANC root IDs. A root-to-stable-ID bridge is therefore the shortest remaining route to an exact cell-level identity.

## Public audit

The 13 frozen FANC roots were searched individually across indexed public GitHub repositories.

All 13 have independent public sightings outside the frozen NeuroFly file:
- most in `tuthill-lab/Lesser_Azevedo_2023`
- one also in `EllenLesser/Azevedo_Lesser_Phelps_Mark_2023`
- all remain present in `sagrawal/Lee_2024`

No indexed public file was recovered that contains both:
- one of the 13 FANC roots and an explicit `SNpp41` mapping, or
- one of the 13 FANC roots and a stable FANC `cell_id` suitable for joining to BANC match products.

The Lee 2024 notebooks confirm that `cell_ids_v2` is the relevant CAVE table, but the checked-in notebook does not contain a cached output mapping these 13 roots to stable IDs.

## Independent type ontology check

The FlyBase anatomy ontology repository maps:

`SNpp41 -> FBbt:00049558 -> femoral chordotonal hook neuron`

This supports the type-level interpretation, but it does not identify an individual FANC cell and therefore cannot close the acceptance gate.

## Machine-readable matrix

`data/research/feco/fanc_v840_hook_flx_bridge_matrix.csv`

records the 13-root bounded search space and current bridge state.

## Current boundary

Resolved:
- MaleCNS 911942 is SNpp41
- BANC 720575941508169089 is SNpp41
- SNpp41 is formally a femoral chordotonal hook neuron
- 13 FANC v840 T1L hook_flx roots are known

Unresolved:
- root -> stable FANC cell ID for the 13 roots
- SNpp41 -> one specific FANC hook_flx cell
- curated individual-cell identity
- exact polarity verification

## Gate state

- bridge_is_type_exclusive: false
- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked

## Next route

Target a public or authenticated export of FANC `cell_ids_v2` (or an equivalent stable-ID table) for only these 13 roots. Once stable IDs are obtained, join them directly against BANC FANC-match products. Do not reopen morphology-only acceptance or retired candidate 20201.
