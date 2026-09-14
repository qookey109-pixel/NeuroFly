# V0.11 SNpp41 Body 905407 SWC Asset Audit

Status: frozen exact SWC asset verification; no peer comparison and no stimulation/current.

## Goal
Download the exact SWC attached to the frozen VFB identity for MaleCNS body `905407` and freeze the real asset bytes plus deterministic basic skeleton statistics.

## Frozen source identity from previous gate

- MaleCNS body: `905407`
- type: `SNpp41`
- VFB individual: `VFB_jrmc173b`
- SWC URL: `https://www.virtualflybrain.org/data/VFB/i/jrmc/173b/VFB_00200000/volume.swc`

PR #53 freezes the identity/source mapping. This gate verifies the actual SWC content independently.

## Discovery run
The first structurally valid SWC discovery was workflow `34821226285`.

The unit gate passed and the real VFB SWC downloaded and parsed successfully. The workflow then intentionally returned `DISCOVERY_REQUIRED` because the asset and statistics hashes were not yet frozen.

Frozen SWC byte SHA256:

`a85f11d845f885c15ca9f79743e79a1a19e3a85000f0997e5ccc0e4be8f08211`

Frozen deterministic statistics SHA256:

`07350bda394d0e8a61b6b1285abb825af0a6f607620d7431f4a8ea4205ac4eea`

Observed skeleton statistics:

- node count: **208**
- root count: **1**
- terminal nodes: **15**
- branch points: **13**
- total parent-child cable length: **120.897291**
- X range: **79.061429 .. 121.686376**
- Y range: **101.585037 .. 130.543583**
- Z range: **59.092176 .. 83.730040**
- node types: `0 = 180`, `5 = 13`, `6 = 15`

Discovery artifact:

- artifact ID: `10338321792`
- ZIP SHA256: `e0b77c0836939b06591c3fe2557ad8bd567443848c8b81a3be746d94ed4ed7a5`

## Frozen verification
The audit now pins both the exact SWC byte SHA and exact normalized statistics SHA. A rerun passes only if both reproduce.

A one-byte source change is therefore distinguishable even if a future parser happened to derive the same summary statistics. Conversely, a statistics change also fails the structural receipt.

## Hard locks
Regardless of SWC result:

- `peer_morphology_compared=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

A green frozen SWC receipt establishes only that the exact target morphology asset is reproducible and moves this evidence gate to `REVIEW_REQUIRED`.

## Scientific boundary
These statistics describe one SWC skeleton. They are not a morphology-similarity score and do not establish that body `905407` belongs with the 21 chordotonal SNpp41 peers.

Connectivity statistics from PR #50 remain separate evidence. No connectivity result is used to pass this morphology-asset gate.

## Next gate
After frozen target-SWC verification is green, resolve and freeze SWC assets for the 21 chordotonal `SNpp41` peers, then predeclare a separate peer morphology comparison method before looking at the target's rank under that method.

No `SNpp39/SNpp41 -> extension/flexion` identity is inferred here.
