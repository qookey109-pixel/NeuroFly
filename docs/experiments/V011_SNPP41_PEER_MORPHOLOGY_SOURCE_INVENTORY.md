# V0.11 SNpp41 Peer Morphology Source Inventory

Status: frozen VFB identity/source inventory; no peer SWC byte freeze, no morphology comparison, no stimulation/current.

## Goal
Resolve the exact public VFB individual and SWC source URL for each of the **21 chordotonal SNpp41 peer bodies** frozen by the body-905407 connectivity receipt.

This stage prepares a controlled morphology cohort. It does not download/freeze the peer SWC bytes and does not compare morphology yet.

## Frozen peer population

The peer body IDs come directly from the reproduced PR #50 connectivity receipt:

`807970, 808576, 809027, 809102, 809353, 812228, 813147, 813644, 814628, 816362, 816580, 817154, 817298, 819524, 819559, 820887, 822285, 824107, 826386, 911942, 936031`

Body `905407` is explicitly excluded because it is the target exception under review.

## Authority and exact identity rule
For each frozen body ID the workflow queries VFB's official read-only API. Numeric body-ID search is combined with the systematic `SNpp41` search, but a candidate is accepted only when `/get_term_info` contains the **exact** MaleCNS body accession.

The audit requires:

- exactly 21 frozen peer body IDs;
- exactly one VFB term cross-referencing each exact MaleCNS body ID;
- at least one SWC URL attached to every resolved peer.

Substring/fuzzy matches are rejected.

## Discovery history
The first structurally useful run exposed an exact-ID matching bug (`80797` incorrectly matching `807970` by substring). That code bug was fixed without changing the cohort or science gates.

After exact matching, body-ID and type search resolved 18/21 peers. Three peers remained missing from the search indexes:

- `819524`
- `819559`
- `911942`

The resolved VFB records occupy the `VFB_jrmc173*` source batch. The three absent namespace slots `VFB_jrmc1739`, `VFB_jrmc173f`, and `VFB_jrmc173g` were therefore probed **diagnostically only**. Namespace adjacency was not accepted as identity evidence; each term still had to expose the exact MaleCNS accession.

Run `34822374243` established:

- `819524 -> VFB_jrmc1739 -> .../1739/VFB_00200000/volume.swc`
- `819559 -> VFB_jrmc173g -> .../173g/VFB_00200000/volume.swc`
- `911942 -> VFB_jrmc173f -> .../173f/VFB_00200000/volume.swc`

All **21/21** peer identities are now unique and all **21/21** have SWC sources.

Frozen canonical inventory SHA256:

`5c7e7bcf85553c5cda5ae1688d3e66f17121171f7cde87891edce60dc5451f65`

Discovery artifact:

- workflow: `34822374243`
- artifact ID: `10338892003`
- ZIP SHA256: `b7246d240a209434b0ce287c4410cd668c01693c498007dd53fd244e48c0bfc9`

## Frozen verification
`EXPECTED_INVENTORY_SHA256` now pins the canonical body→VFB→SWC inventory. A rerun passes only when the exact 21-peer population, identities, and source URLs reproduce.

The receipt is a reproducibility gate, **not** a biological morphology-similarity threshold.

## Hard locks
Regardless of inventory result:

- `peer_morphology_assets_frozen=false`
- `peer_morphology_compared=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

## Next gates
After the frozen source inventory reproduces:

1. download and freeze the byte SHA/statistics receipt for every one of the 21 peer SWCs;
2. predeclare a morphology-comparison method using only the peer cohort, before examining body `905407`'s rank;
3. run the target-vs-peer morphology comparison as a separate gate.

Connectivity evidence remains separate. No extension/flexion tuning identity is inferred here.
