# V0.11 SNpp41 Body 905407 Morphology Envelope Audit

Status: read-only target comparison against a protocol frozen **before** target evaluation.

## Goal

Apply the frozen peer-only SNpp41 morphology protocol to MaleCNS body `905407` without changing any feature, normalization, distance, or threshold after seeing the target.

## Frozen authority

- target body: `905407`
- VFB individual: `VFB_jrmc173b`
- frozen target SWC SHA256: `a85f11d845f885c15ca9f79743e79a1a19e3a85000f0997e5ccc0e4be8f08211`
- frozen target stats SHA256: `07350bda394d0e8a61b6b1285abb825af0a6f607620d7431f4a8ea4205ac4eea`
- frozen peer morphology protocol receipt SHA256: `9710b3456c599af24d896a6e9b9f0b577c73cdc0eae6a3ac9260c1baf5ed8c48`
- frozen peer envelope threshold: `1.833618426632`

## Procedure

1. Reproduce the frozen peer-only protocol from the exact 21 peer SWCs.
2. Require its protocol receipt to match exactly.
3. Download body `905407`'s already frozen SWC asset.
4. Require its SWC byte SHA and statistics SHA to match the frozen target asset receipt.
5. Compute the exact predeclared 10-feature descriptor.
6. Compute its RMS robust-standardized distance to every frozen peer descriptor.
7. Select the nearest peer.
8. Apply the predeclared gate only:

`target_nearest_peer_distance <= 1.833618426632`

No post-hoc threshold or feature change is allowed.

## Scientific boundary

A pass means only that body `905407` lies inside this **coarse topology/geometry descriptor envelope** relative to the frozen SNpp41 peers.

It does not establish receptor physiology, functional identity, movement-phase tuning, extension/flexion assignment, or behavioral causality.

## Hard locks

Regardless of result:

- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

Any proprioceptive stimulation/current remains blocked behind separate biological/tuning and frozen calibration evidence.
