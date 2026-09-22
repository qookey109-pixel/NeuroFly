# V1 public MANC sensory-match audit

## Question

Does the author-published public sensory-match CSV explicitly connect the frozen
MANC SNpp41 target (`MANC 97015`) to either the BANC-reported FANC candidate
`cell_id=20201` or one of the five current FANC `hook_flx` roots frozen by
PR #124?

## Author publication path

Pinned pipeline source:

- repository: `htem/bancpipeline`
- commit: `5c333c12f0b9e03873f88cf4e23cad34c0bb49c1`
- file: `setup/hms_setup.R`

That source explicitly uploads:

`2024-09-02_manc_sensory_matches.csv`

to the public bucket:

`gs://lee-lab_brain-and-nerve-cord-fly-connectome/neuron_searches`

The audit fetches the corresponding public HTTPS object directly.

## Exact targets

- MANC body: `97015`
- systematic type: `SNpp41`
- BANC FANC candidate cell ID: `20201`
- PR #124 current FANC hook-flexion roots:
  - `648518346481857725`
  - `648518346509569667`
  - `648518346494933426`
  - `648518346514448583`
  - `648518346494264434`

## Decision rule

Only exact token co-occurrence in the same author-published CSV row is accepted
as a direct bridge candidate.

The audit does **not** use:

- same-number inference across namespaces;
- morphology or NBLAST recomputation;
- spatial proximity;
- root-family inference;
- file order or adjacency.

Even a positive same-row hit is frozen as evidence for later review and does not
automatically set `curated_fanc_to_manc_snpp_bridge_found=true` or open the
polarity/runtime/calibration gates.
