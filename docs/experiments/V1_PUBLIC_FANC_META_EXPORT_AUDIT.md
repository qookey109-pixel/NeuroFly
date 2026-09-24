# V1 public FANC metadata export audit

## Question

Is the BANC pipeline's FANC `cell_id <-> root_id` metadata now available
through any public GCS export, even though the pipeline historically documented
the compiled FANC metadata feather as unpublished?

This matters because the unvalidated BANC morphology candidate is
`FANC cell_id=20201`, while PR #124 froze five exact `hook_flx` FANC roots.

## Authoritative mapping semantics

Pinned `htem/bancpipeline` source:

- commit: `5c333c12f0b9e03873f88cf4e23cad34c0bb49c1`
- `fanc/fanc-meta.R`

The pipeline explicitly builds:

`cell_ids_v2 |> distinct(cell_id = id, pt_root_id, ...)`

and later renames `pt_root_id -> root_id`.

Therefore a public row with both `cell_id` and `root_id` is sufficient to
resolve the FANC namespace mapping without number guessing or morphology.

## Public objects tested

The audit checks likely historical/current paths including:

- `meta/fanc_meta.csv`
- `meta/fanc_meta.feather`
- `compiled_data/fanc_1116/fanc_meta.csv`
- `compiled_data/fanc_1116/fanc_1116_meta.feather`

It also anonymously lists FANC-related prefixes and probes newly discovered
CSV/Feather metadata objects.

## Exact targets

- FANC cell ID: `20201`
- frozen hook-flexion roots:
  - `648518346481857725`
  - `648518346509569667`
  - `648518346494933426`
  - `648518346514448583`
  - `648518346494264434`

Only an exact same-row `cell_id=20201` + one of those roots is reported as a
namespace bridge.

## Governance

Even a positive namespace bridge does not validate the BANC morphology match:
that row remains `score=0.1`, `validation=false`, and cannot by itself
establish a curated FANC↔MANC/SNpp41 identity or unlock polarity/calibration/
runtime stimulation.


## Observed result (2026-09-24)

The public GCS probe completed successfully.

Results:

- `existing_candidate_object_count = 0`
- `parseable_metadata_object_count = 0`
- `cell_id_20201_found_in_public_metadata = false`
- `exact_20201_to_hook_flx_root_found = false`

None of the explicit candidate objects exists publicly:

- `meta/fanc_meta.csv`
- `meta/fanc_meta.feather`
- `meta/fanc_1116_meta.csv`
- `meta/fanc_1116_meta.feather`
- `compiled_data/fanc_1116/fanc_meta.csv`
- `compiled_data/fanc_1116/fanc_meta.feather`
- `compiled_data/fanc_1116/fanc_1116_meta.csv`
- `compiled_data/fanc_1116/fanc_1116_meta.feather`

The FANC compiled-data prefix remains dominated by
`compiled_data/fanc_1116/fanc_banc_space_swc/<root_id>.swc` objects.

Interpretation: the BANC pipeline's local `fanc_meta.csv` is still not
available as a direct public root↔cell-ID table. This is a public-export
boundary, not evidence about biological identity.
