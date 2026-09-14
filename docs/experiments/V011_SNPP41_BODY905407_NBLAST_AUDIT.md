# V0.11 SNpp41 Body 905407 Registered-Space NBLAST Audit

Status: discovery-first; no stimulation; no proprioceptive current calibration.

## Goal

Add a stronger **shape-comparison** evidence layer for MaleCNS body `905407` after the raw-SWC morphology receipt in PR #51.

This gate does not reuse native-space cable length or bounding-box thresholds. Instead it compares body `905407` with the 21 clean `SNpp41 / chordotonal organ` peers after all skeletons have already been transformed by MaleCNS into the common **JRC2018 unisex (`JRC2018U`) template space**.

## Registered source authority

MaleCNS v1.0 officially publishes:

`gs://flyem-male-cns/v1.0/segmentation/skeletons-unisex-template/`

The MaleCNS download documentation states that these skeletons are transformed to JRC2018 unisex template space and use **1 µm units**.

Source: https://male-cns.janelia.org/download/

The audit discovers each body object's exact public Google Cloud Storage name and records its generation, size, storage hashes and SHA256. It fails closed if a body resolves to zero or multiple registered skeleton objects.

## Morphology/NBLAST toolchain pins

- `navis==1.12.0`
- `flybrains==0.6.2`
- NBLAST scoring-matrix repository: `flyconnectome/nblast-scoremats`
- exact score-matrix commit: `e2a5b027a7afe968c05ad1ac375ef3f25037f7fd`
- matrix: `scoremats/smat_flywire_mcns.across_hemisphere.free_bins.csv`

The scoring-matrix project documents this FlyWire + MaleCNS matrix for comparisons that involve transforms/mirroring. Units are micrometers.

The score-matrix bytes are downloaded from the exact commit and their SHA256 is part of the discovery receipt.

## NBLAST parameters

- dotprops `k=5`
- resample spacing: `1 µm`
- `normalized=true`
- `scores="mean"`
- `use_alpha=false`
- one core for deterministic execution

Mean scoring is used because NBLAST is directional: it averages forward and reverse comparisons.

## Side-invariant comparison

Body `905407` has no frozen soma-side annotation. We therefore do **not** assign it an artificial side.

JRC2018U is a mirror-symmetric template. For each pair, the audit evaluates:

1. original query vs original target (`oo`)
2. original query vs mirrored target (`om`)
3. mirrored query vs original target (`mo`)
4. mirrored query vs mirrored target (`mm`)

The pair's descriptive score is the maximum of those four variants.

All four raw score matrices remain in the canonical receipt. Mirroring is only an alignment device; it is not a biological laterality claim.

## Population

Target:
- body `905407`
- type `SNpp41`
- class `mechanosensory_proprioceptive`
- subclass `leg`

Peers:
- same type/class
- subclass `chordotonal organ`
- exact expected count: 21

Peer identity comes from the same pinned prepared MaleCNS annotation table used by the prior gates.

## Discovery-first policy

`EXPECTED_NBLAST_SHA256` starts unset.

The first prepared run records:

- exact registered skeleton object identity and SHA for all 22 bodies;
- pinned package versions;
- exact scoring-matrix identity and byte SHA;
- all four pairwise NBLAST score matrices;
- best mirror-corrected pair scores;
- target-vs-peer scores;
- leave-one-out peer median distribution;
- target median and its descriptive percentile among peer medians;
- deterministic canonical receipt SHA256.

If every structural/source/toolchain gate passes, the first run intentionally exits non-zero as `DISCOVERY_REQUIRED` while still publishing the artifact.

**No NBLAST acceptance threshold is chosen after seeing the result.** A later commit may freeze the exact receipt solely for reproducibility.

## Hard locks

Even a reproducible NBLAST receipt must keep:

- `promotion_ready=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `current_calibration_authorized=false`
- `direction_tuning_resolved=false`

A green frozen receipt means `REVIEW_REQUIRED`, not promotion.

## What this gate cannot prove

NBLAST similarity can provide stronger morphological-consistency evidence than raw bounding boxes, but it still does not resolve sensory tuning. In particular, this gate does **not** establish:

- that body `905407` is biologically interchangeable with every SNpp41 peer;
- whether `SNpp39` is extension- or flexion-tuned;
- whether `SNpp41` is extension- or flexion-tuned;
- a proprioceptive external current amplitude;
- runtime proprioceptive stimulation;
- behavioral benefit.

Current calibration remains blocked until direction/function mapping has direct evidence independent of this shape score.
