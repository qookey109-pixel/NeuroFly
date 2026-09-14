# V0.11 SNpp41 Body 905407 Morphology Source Audit

Status: frozen external morphology-source verification; no stimulation/current.

## Goal
Resolve body `905407` to an exact Virtual Fly Brain individual record and confirm that independent morphology assets are publicly attached to that exact individual.

Connectivity evidence from PR #50 is intentionally not reused as morphology evidence.

## Authority
The workflow queries VFB's current read-only VFBquery API at `https://v3-cached.virtualflybrain.org` using:

- `/search?query=905407`
- `/search?query=SNpp41`
- `/get_term_info?id=<candidate VFB id>`

## Discovery run
First external discovery run: `34819555866`.

The run intentionally ended `DISCOVERY_REQUIRED` after the structural gates succeeded and the artifact was published.

Exact body `905407` resolved to one VFB individual:

- `VFB_jrmc173b`

The exact VFB term exposes morphology assets:

- SWC: `https://www.virtualflybrain.org/data/VFB/i/jrmc/173b/VFB_00200000/volume.swc`
- OBJ: `https://www.virtualflybrain.org/data/VFB/i/jrmc/173b/VFB_00200000/volume_man.obj`
- NRRD: `https://www.virtualflybrain.org/data/VFB/i/jrmc/173b/VFB_00200000/volume.nrrd`

Frozen canonical VFB source receipt SHA256:

`f1ff278a2c40691987f2de473302fcc259df3ad854f0b8c942eb05c7127067da`

Discovery artifact:

- artifact ID: `10337811668`
- ZIP SHA256: `7fbcfaea254ab60bf735861595d45da38c485d7354f76d06d42edbfafe58c35e`

## Frozen verification
The source audit now pins both:

- expected VFB ID `VFB_jrmc173b`
- expected source receipt SHA256 `f1ff278a2c40691987f2de473302fcc259df3ad854f0b8c942eb05c7127067da`

A future run passes only if the body accession still resolves to exactly one VFB individual and the canonical source payload is byte-for-byte equivalent after normalization. Any identity/source drift fails closed.

## Hard locks
Regardless of source verification result:

- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

A green frozen source receipt means only `REVIEW_REQUIRED`.

## Scientific boundary
This gate establishes an independent public morphology **source** for body `905407`. It does not yet establish that the target morphology matches the 21 chordotonal SNpp41 peers.

The actual SWC bytes have not yet been frozen or quantitatively compared in this gate. Connectivity similarity remains separate evidence and cannot substitute for skeleton morphology.

## Next gate
After the frozen source verification is green, download the exact `VFB_jrmc173b` SWC, freeze its byte SHA256 and basic skeleton statistics, and compare the target morphology against chordotonal SNpp41 peer skeletons in a separate audit.

No extension/flexion tuning identity is inferred here.
