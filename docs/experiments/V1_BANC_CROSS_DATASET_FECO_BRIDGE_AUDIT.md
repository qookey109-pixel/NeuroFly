# V1 BANC Cross-Dataset FeCO Bridge Audit

Status: **READ-ONLY EVIDENCE PROBE — NO POLARITY UNLOCK**

## Why this layer exists

PR #120 recovered the five original Phelps/GridTape FANC source neurons behind
the author-generated R21D12 top-five EM morphology hits:

- 25849
- 25842
- 25856
- 24831
- 25909

Those identifiers belong to the legacy Phelps CATMAID/FANC source namespace.
They must not be treated as BANC's current FANC v1.116 match IDs without an
explicit namespace bridge.

## New independent downstream evidence

The BANC 2026 paper repository publishes Supplementary Data 2 with explicit
cross-dataset match columns.

The proofread BANC neuron `720575941508169089` is:

- `SNpp41`
- `middle_leg_hook_chordotonal_organ_neuron`
- `manc_match = 97015`
- `malecns_match = 911942`

This independently confirms the already frozen MANC/MaleCNS SNpp41 bridge.

## FANC ID semantics

The BANC pipeline documents its BANC↔FANC CAVE product as:

- query ID: BANC root ID
- `match_id`: **FANC cell_id**
- `validation`: manual-review confirmation flag

This is deliberately kept separate from both FANC segmentation root IDs and
the older Phelps CATMAID skeleton IDs.

## Probe question

For BANC root `720575941508169089`, does the public
`banc_fanc_1116_nblast.feather` contain an author-validated FANC v1.116
`cell_id` match?

The probe only reports precomputed author data. It does not run NBLAST or any
new morphology comparison.

## Governance

Even a validated current-FANC match would not by itself prove that R21D12 is a
single FANC cell, because PR #120's R21D12 evidence remains a ranked morphology
set rather than a curated one-to-one assignment.

Until an explicit legacy/current FANC namespace and cell-level identity chain
is recovered:

- `curated_r21d12_to_specific_fanc_em_identity_found = false`
- `curated_fanc_to_manc_snpp_bridge_found = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked
