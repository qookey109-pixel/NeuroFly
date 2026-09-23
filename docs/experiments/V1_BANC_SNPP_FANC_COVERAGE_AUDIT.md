# V1 BANC SNpp39/SNpp41 FANC coverage audit

## Question

Does BANC Supplementary Data 2 contain **any** published FANC match for
`SNpp39` or `SNpp41`, and especially for the exact NeuroFly target chain:

`BANC 720575941508169089 -> SNpp41 -> MANC 97015 -> MaleCNS 911942`?

## Why this audit exists

A quick ad-hoc check previously split the `.txt` file on tab characters and
returned zero SNpp39/SNpp41 rows. That result is invalid: the publication file
is CSV-like and the earlier PR #121 audit successfully parsed its target row
with Python `csv.DictReader`.

This audit detects the delimiter explicitly and scans the full publication
table.

## Positive rule

The strongest candidate is an **exact same published row** containing:

- `cell_type = SNpp41`;
- `cell_sub_class = middle_leg_hook_chordotonal_organ_neuron`;
- `manc_match = 97015`;
- `malecns_match = 911942`;
- a non-missing `fanc_match`.

Any FANC match found only on a different SNpp39/SNpp41 instance is reported as
context. It is not transferred across leg segment or side by systematic type
name, preserving the NeuroFly #116 guard.

## Governance

This is an evidence audit only. It does not automatically alter polarity,
calibration, runtime stimulation, or privileged-state locks.


## Observed result (2026-09-23)

The corrected full-table audit successfully parsed the publication source:

- delimiter: comma;
- total rows: `155927`;
- `SNpp39`: `99` rows, `21` rows with published `fanc_match`;
- `SNpp41`: `66` rows, `6` rows with published `fanc_match`;
- exact target BANC root `720575941508169089`: `fanc_match=NA`;
- all `manc_match=97015` rows: `9`, with FANC match count `0`;
- `malecns_match=911942`: one exact row, with FANC match count `0`;
- exact same-row SNpp41/MANC97015/MaleCNS911942/FANC bridge: `0`.

The BANC↔FANC feather was then joined by exact
`(BANC root_id, published fanc_match)` for proofread hook rows:

- exact joins: `12`;
- validated joins: `12/12`;
- SNpp39 validated joins: `7`;
- SNpp41 validated joins: `5`;
- every joined `match_cell_type`: `null`;
- replicated directional type crosswalk: `false`.

Critically, several published FANC IDs are shared across BANC SNpp39 and SNpp41
instances (including `3889`, `1168`, `1163`, and `1378`). Therefore
these cross-dataset matches cannot be used as a type-exclusive polarity bridge.
This independently reinforces the NeuroFly #116 same-name/type-exclusivity
guard.

The result is useful positive provenance for curated BANC↔FANC matches, but it
does not resolve the exact SNpp39/SNpp41 flexion-extension polarity.
