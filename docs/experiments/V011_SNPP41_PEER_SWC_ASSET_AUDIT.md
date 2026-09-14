# V0.11 SNpp41 Peer SWC Asset Audit

Status: discovery-first exact-byte and skeleton-statistics audit for the 21 frozen chordotonal `SNpp41` peers. No morphology comparison, tuning inference, current calibration, stimulation, or runtime transduction is authorized here.

## Goal

Download the actual public VFB SWC bytes for the exact 21-peer morphology cohort frozen by the upstream source inventory and compute reproducible byte/statistics receipts using the **same parser and statistics implementation already frozen for target body `905407`**.

This keeps the target and peer cohort on one measurement implementation before any morphology comparison is attempted.

## Frozen upstream authority

Source inventory SHA256:

`5c7e7bcf85553c5cda5ae1688d3e66f17121171f7cde87891edce60dc5451f65`

The exact body→VFB→SWC mapping is inherited from PR #55. Body `905407` is excluded from the peer cohort.

## Per-peer receipt

For each exact peer the audit downloads its `volume.swc` and records:

- raw SWC byte SHA256;
- node count;
- root count;
- terminal-node count;
- branch-point count;
- total Euclidean cable length;
- X/Y/Z bounding box;
- SWC node-type counts;
- canonical statistics SHA256.

The parser/statistics functions are imported directly from `proprioception_swc_asset_audit.py`, the already validated body-905407 asset audit.

## Discovery-first gate

`EXPECTED_COHORT_RECEIPT_SHA256` starts unset.

If all 21 exact peer assets download and parse cleanly, the first external workflow run must return `DISCOVERY_REQUIRED` and publish the canonical cohort receipt. A later evidence commit may freeze only that exact receipt SHA.

The cohort receipt includes every peer's exact identity, SWC URL, byte SHA, statistics, and statistics SHA. Therefore any later byte or structural-statistics drift changes the cohort receipt.

## Structural fail-closed rules

The audit fails if any of the following occurs:

- peer count or body-ID set differs from the frozen 21-peer source inventory;
- target body `905407` appears in the cohort;
- a body→VFB→SWC identity differs from the frozen source inventory;
- a SHA256 is malformed;
- a statistics object does not reproduce its recorded stats SHA;
- any peer skeleton is empty or has no root.

## Hard locks

Regardless of result:

- `peer_morphology_compared=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

Only after the exact cohort receipt reproduces may a later PR predeclare a morphology-comparison method using peer-only information before examining body `905407`'s rank.

No `SNpp39/SNpp41 -> extension/flexion` tuning identity is inferred by this asset audit.
