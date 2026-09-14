# V0.11 SNpp41 Peer SWC Asset Audit

Status: **frozen verification PASS** for the exact-byte and skeleton-statistics cohort of the 21 frozen chordotonal `SNpp41` peers. No morphology comparison, tuning inference, current calibration, stimulation, or runtime transduction is authorized here.

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

## Discovery run

Workflow run `34824218714` completed the full external discovery. Unit tests passed and all 21 exact peer SWCs downloaded and parsed successfully.

All structural gates passed:

- exact peer count = 21;
- exact frozen peer body-ID set preserved;
- body `905407` excluded;
- body→VFB→SWC identities matched the frozen PR #55 inventory;
- all SWC/statistics SHA256 values were well formed;
- all statistics receipts were self-consistent;
- every skeleton was non-empty and had at least one root.

The run intentionally returned `DISCOVERY_REQUIRED` only because no cohort receipt had yet been frozen.

Frozen cohort receipt SHA256:

`aeba54052eb7a53c1c1e9b7f6bf1a7fb1010baa3023db9b693af9f3e3e6e70d2`

Discovery artifact:

- artifact ID `10338724229`
- ZIP SHA256 `7359c0057e32c2f110add00b02d52036916b3bbe0c7ece41325878e0ab2b3bc8`

## Frozen verification

The exact cohort receipt above is now pinned in code. Workflow run `34825439017` reproduced the full 21-peer cohort and completed successfully.

Frozen verification artifact:

- artifact ID `10339737552`
- ZIP SHA256 `4f745dcbaf980ab441bb6a800ad3ee40083bc65b42bf8f60ca2a208978f32c95`

A passing frozen verification means only that the exact peer SWC assets and deterministic descriptive skeleton statistics are reproducible. It does **not** imply that body `905407` is morphologically typical, similar, functionally equivalent, or tuned for any particular movement phase.

## Structural fail-closed rules

The audit fails if any of the following occurs:

- peer count or body-ID set differs from the frozen 21-peer source inventory;
- target body `905407` appears in the cohort;
- a body→VFB→SWC identity differs from the frozen source inventory;
- a SHA256 is malformed;
- a statistics object does not reproduce its recorded stats SHA;
- any peer skeleton is empty or has no root;
- the full frozen cohort receipt changes.

## Hard locks

Regardless of result:

- `peer_morphology_compared=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

Only after this exact cohort receipt reproduces may a later PR predeclare a morphology-comparison method using peer-only information before examining body `905407`'s rank.

No `SNpp39/SNpp41 -> extension/flexion` tuning identity is inferred by this asset audit.
