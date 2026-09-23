# V1 FeCO hook motor-sign concordance audit

## Question

Can an independent FANC connectivity-derived motor-module classification
distinguish Lee's `hook_flx` and `hook_ext` populations in the same sign
predicted for MANC `SNpp41` and `SNpp39`?

This is deliberately **not** a one-cell identity audit.

## Sources

### FANC directional identity

Pinned Lee 2024:

- repo: `sagrawal/Lee_2024`
- commit: `4328b1d5549749f1014c4d73cccc0c5241d98ae4`
- table: `synapse_tables/feco_annotation_table.csv`

The static table supplies exact T1L `hook_flx/hook_ext`,
`pt_supervoxel_id`, and `pt_root_id`.

### Independent preferred motor module

Pinned Lesser/Azevedo 2023:

- repo: `tuthill-lab/Lesser_Azevedo_2023`
- commit: `93cafa55b8bbdb1493e8d73c941035969349b223`
- `jsons/v840/preferred_module_*_sensory.json`
- generator: `jsons/make_jsons/generate_links_and_table.ipynb`
- module semantics: `utils.py`

The author generator groups sensory `segID` values by `cell_class` and
`preferred_module`. The utility definitions identify `tibia_extend` as the
femur-joint extension module targeting tibia extensor motor neurons.

### MANC signed circuit

This audit reuses the merged PR #113 receipt
`data/feco_hook_polarity_crosscheck_v01.json`, which freezes the published
signed circuit:

- SNpp41 inhibits tibia flexor/accessory flexor via IN19A015 and activates tibia
  extensor.
- SNpp39 inhibits tibia extensor via IN19A005 and disinhibits tibia flexors.

The original source is the MANC systematic annotation reviewed preprint,
DOI `10.7554/eLife.97766.1`.

## Decision rule

The audit requires both directional populations to separate without crossed
tibia preference:

- `hook_flx`: majority tibia-extensor preferred and zero tibia-flexor preferred;
- `hook_ext`: majority tibia-flexor preferred and zero tibia-extensor preferred.

Other-module and unassigned cells are retained, not discarded.

The five Phelps/R21D12 candidate roots from PR #124 are reported separately.

## Governance

A positive result strengthens the type-level functional-sign crosswalk:

- `SNpp41 ↔ hook flexion candidate`
- `SNpp39 ↔ hook extension candidate`

It does **not** establish a curated one-cell FANC↔MANC identity and therefore
does not automatically set `exact_polarity_verified=true`, authorize
Calibration, or authorize runtime stimulation.
