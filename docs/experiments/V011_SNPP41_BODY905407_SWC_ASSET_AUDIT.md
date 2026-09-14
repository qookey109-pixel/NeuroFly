# V0.11 SNpp41 Body 905407 SWC Asset Audit

Status: discovery-first exact SWC asset gate; no peer comparison and no stimulation/current.

## Goal
Download the exact SWC attached to the frozen VFB identity for MaleCNS body `905407` and freeze the real asset bytes plus deterministic basic skeleton statistics.

## Frozen source identity from previous gate

- MaleCNS body: `905407`
- type: `SNpp41`
- VFB individual: `VFB_jrmc173b`
- SWC URL: `https://www.virtualflybrain.org/data/VFB/i/jrmc/173b/VFB_00200000/volume.swc`

PR #53 freezes the identity/source mapping. This gate verifies the actual SWC content independently.

## Discovery-first design
The first workflow run is expected to end `DISCOVERY_REQUIRED` because the SWC byte SHA256 and stats SHA256 are intentionally unset.

The audit downloads the SWC, validates its parent graph, and reports:

- SWC byte SHA256
- node count
- root count
- terminal-node count
- branch-point count
- total parent-child cable length
- XYZ bounding box
- SWC node-type counts
- deterministic statistics SHA256

No biological similarity threshold is defined in this stage.

## Hard locks
Regardless of SWC result:

- `peer_morphology_compared=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

A later green frozen SWC receipt establishes only that the exact morphology asset is reproducible.

## Next gate
After freezing the actual SWC byte/statistics receipt, resolve and freeze SWC assets for the 21 chordotonal `SNpp41` peers and perform a separate morphology comparison. Connectivity statistics from PR #50 remain independent evidence.

No `SNpp39/SNpp41 -> extension/flexion` identity is inferred here.
