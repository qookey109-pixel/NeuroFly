# V0.11 SNpp41 Peer Morphology Source Inventory

Status: discovery-first identity/source inventory; no morphology comparison and no stimulation/current.

## Goal
Resolve the exact public VFB individual and SWC source URL for each of the **21 chordotonal SNpp41 peer bodies** frozen by the body-905407 connectivity receipt.

This stage prepares a controlled morphology cohort. It does not download/freeze the peer SWC bytes and does not compare morphology yet.

## Frozen peer population

The peer body IDs come directly from the reproduced PR #50 connectivity receipt:

`807970, 808576, 809027, 809102, 809353, 812228, 813147, 813644, 814628, 816362, 816580, 817154, 817298, 819524, 819559, 820887, 822285, 824107, 826386, 911942, 936031`

Body `905407` is explicitly excluded because it is the target exception under review.

## Authority
For each frozen body ID the workflow queries VFB's official read-only API:

- `/search?query=<bodyId>`
- `/get_term_info?id=<candidate VFB id>`

The audit requires:

- exactly 21 frozen peer body IDs;
- exactly one VFB term cross-referencing each exact MaleCNS body ID;
- at least one SWC URL attached to every resolved peer.

Any missing, ambiguous, or SWC-less peer fails structurally.

## Discovery-first design
`EXPECTED_INVENTORY_SHA256` starts unset. If all 21 sources resolve cleanly, the first external run deliberately returns `DISCOVERY_REQUIRED` and publishes the canonical body→VFB→SWC inventory.

The next evidence commit may freeze only that exact inventory SHA. This is a reproducibility receipt, not a biological similarity threshold.

## Hard locks
Regardless of inventory result:

- `peer_morphology_assets_frozen=false`
- `peer_morphology_compared=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

## Next gates
After a frozen source inventory reproduces:

1. download and freeze the byte SHA/statistics receipt for every peer SWC;
2. predeclare a morphology-comparison method using only the peer cohort, before examining body `905407`'s rank;
3. run the target-vs-peer morphology comparison as a separate gate.

Connectivity evidence remains separate. No extension/flexion tuning identity is inferred here.
