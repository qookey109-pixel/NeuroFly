# V1 public FANC raw NBLAST audit

## Why this route matters

The pinned BANC↔FANC NBLAST compute script writes a raw CSV per BANC query.
Before compilation, each candidate row contains both:

- `fanc_match` = FANC root ID
- `cell_id` = FANC `cell_ids_v2.id`

The compiled public feather later emits `match_id=cell_id` and no longer keeps
the FANC root ID.

For the frozen BANC SNpp41 query:

- BANC root: `720575941508169089`
- query supervoxel: `77060647762534032`
- compiled FANC candidate: `cell_id=20201`
- score: `0.1`
- validation: `false`

If the raw CSV is publicly mirrored, its exact `20201` row can resolve the
FANC root namespace without any new morphology calculation.

## Audit

The probe checks:

- public `nblast/banc_fanc_reviewed_matches.csv`;
- public `nblast/` and FANC-related GCS prefixes;
- exact likely raw-result paths for version
  `elastix_tpsreg_240721`;
- any listed object containing the frozen BANC root / raw filename.

Only the author raw CSV's same-row `cell_id=20201` + `fanc_match=<root>`
counts as a namespace mapping.

## Governance

Even if found, this does not upgrade the BANC candidate itself: its
`validation=false` status remains authoritative. No polarity, calibration,
runtime stimulation, or privileged-state lock is opened by this audit.


## Observed result (2026-09-24)

The public `nblast/` bucket listing is readable and non-truncated at its top
level. The compiled FANC feather and reviewed CSV are public, but no raw
per-query CSV for the frozen SNpp41 query is publicly mirrored under any tested
or listed path.

Raw result:

- `public_raw_object_count = 0`
- `public_raw_20201_root_mapping_found = false`
- `resolved_fanc_roots_for_20201 = []`

The public reviewed-match CSV contains exactly one row for the frozen BANC
SNpp41 query:

- `pt_root_id = 720575941508169089`
- `pt_supervoxel_id = 77060647762534032`
- `query_id = 720575941508169089`
- `match_id = NA`
- `match_cell_type = NA`
- `valid = t`

The pinned downstream pipeline imports FANC reviewed matches only as
`fanc_png_match` when a concrete `match_id` survives the reviewed-match
filter. Independently, the final public BANC annotation for this same SNpp41
cell has `fanc_match = NA`.

Therefore the defensible interpretation is narrow: a current/valid reviewed
record exists, but **no FANC match identifier is promoted for this SNpp41
cell**. This does not prove that a reviewer explicitly rejected the numerical
candidate `20201`; it does prove that the reviewed/public pipeline contains no
accepted FANC identity for this query.

Combined with the compiled candidate's `score=0.1`,
`validation=false`, `match_cell_type=null`, and the public FANC
segment-properties metadata for `20201` (`label=unknown`, tags
`central neuron`, `right`), `20201` is retired as a usable identity
bridge candidate unless a stronger independent source appears.
