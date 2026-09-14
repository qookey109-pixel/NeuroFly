# V0.11 SNpp41 Body 905407 Morphology Source Audit

Status: discovery-first external morphology source gate; no stimulation/current.

## Goal
Resolve body `905407` to an exact Virtual Fly Brain individual record and confirm that independent morphology assets (for example SWC skeleton / OBJ pointcloud or mesh) are publicly attached to that exact individual.

Connectivity evidence from PR #50 is intentionally not reused as morphology evidence.

## Authority
The discovery workflow queries VFB's current read-only VFBquery API at `https://v3-cached.virtualflybrain.org` using:

- `/search?query=905407`
- `/search?query=SNpp41`
- `/get_term_info?id=<candidate VFB id>`

The first run is expected to fail with `DISCOVERY_REQUIRED` until an exact VFB ID and canonical source receipt SHA256 are frozen.

## Hard locks
Regardless of discovery result:

- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

A future green frozen morphology-source receipt means only `REVIEW_REQUIRED`.

## Next gate
If one exact VFB individual cross-references MaleCNS body `905407` and exposes morphology assets, freeze that identity/receipt and re-run. Only after that may a separate morphology-comparison audit compare the target skeleton with chordotonal SNpp41 peers.

No extension/flexion tuning identity is inferred here.
