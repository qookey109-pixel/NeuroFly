# V0.11 SNpp41 Body 905407 Morphology Audit

Status: discovery-first; no stimulation; no proprioceptive current calibration.

## Goal

Obtain **independent morphology evidence** for MaleCNS body `905407`, which is the frozen `SNpp41|leg` row-level exception identified in the prior annotation audit.

This stage deliberately keeps morphology separate from connectivity. PR #50 already froze a synaptic-contact partner fingerprint; this stage asks only whether the official MaleCNS v1.0 centerline skeleton is reproducible and how simple geometry summaries compare descriptively with the 21 `SNpp41` rows annotated as `chordotonal organ`.

## Official source

The MaleCNS project publishes centerline skeletons for all released neurons in SWC format:

`gs://flyem-male-cns/v1.0/segmentation/skeletons-malecns/skeletons-swc/{bodyId}.swc`

The audit uses the HTTPS equivalent:

`https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/skeletons-malecns/skeletons-swc/{bodyId}.swc`

The official download documentation states that these SWC coordinates are in Male CNS EM coordinate space and expressed in 8 nm units.

Source: https://male-cns.janelia.org/download/

## Population

Target:
- body `905407`
- type `SNpp41`
- class `mechanosensory_proprioceptive`
- subclass `leg`

Reference peers:
- exact same type/class
- subclass `chordotonal organ`
- expected count: 21

Peer identity is read from the same pinned prepared MaleCNS annotations used by the previous gates; it is not maintained as a hand-written list.

## Skeleton receipt

For target + 21 peers, the audit freezes/describes:

- raw official SWC SHA256
- node count
- edge count
- root count
- leaf count
- branchpoint count
- total centerline cable length in micrometers
- X/Y/Z bounding-box spans in micrometers

The canonical receipt includes all 22 raw SWC digests and geometry summaries plus descriptive target-vs-peer ranges/percentiles.

## Discovery-first rule

The first prepared run has no expected morphology receipt SHA. If all structural/source gates pass, it writes the evidence artifact and returns `DISCOVERY_REQUIRED` with a non-zero exit code.

Only after inspecting the exact prepared receipt may a later commit freeze its SHA256.

No morphology similarity threshold is selected after seeing the data.

## Hard locks

Even a reproducible morphology receipt must keep:

- `promotion_ready=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `current_calibration_authorized=false`
- `direction_tuning_resolved=false`

A green frozen receipt will mean **REVIEW_REQUIRED**, not promotion.

## What this evidence cannot prove

Simple centerline metrics do not establish that body `905407` is biologically equivalent to every other hook neuron, nor do they resolve whether `SNpp39` or `SNpp41` corresponds to extension vs flexion tuning.

If stronger morphology classification is needed after this receipt is frozen, use an explicit shape-comparison method such as a registered-space/NBLAST-style analysis as a separate evidence gate rather than inventing a cutoff here.
