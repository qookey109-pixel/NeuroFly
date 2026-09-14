# V0.11 SNpp41 Body 905407 Morphology Audit

Status: frozen receipt under verification; no stimulation; no proprioceptive current calibration.

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

## Prepared discovery evidence

Workflow run: `34813875795`

The run intentionally returned `DISCOVERY_REQUIRED` after every structural/source gate passed. Artifact publication also succeeded.

Frozen canonical morphology receipt SHA256:

`a0cfd6206b92bb9179eede4c84bfd15da2b284516dfaebeb5e1b6e3c4d37b597`

Target body `905407` raw official SWC SHA256:

`5934c17b42edc0ea10dc75e571ca258a0321d2b72ecce796f0ee736a606aa174`

Artifact:
- ID: `10335482076`
- ZIP SHA256: `1d03324fd57c36a3a94e914e3c81c9494865e74a3a315ba7830dfefd84577723`

Target centerline summary:
- nodes: `208`
- edges: `207`
- roots: `1`
- leaves: `15`
- branchpoints: `13`
- cable length: `172.063042 µm`
- bounding-box span: X `66.56 µm`, Y `39.936 µm`, Z `33.792 µm`

Descriptive comparison with the 21 chordotonal-organ `SNpp41` peers:

| Metric | Target | Peer min | Peer median | Peer max | Target percentile |
| --- | ---: | ---: | ---: | ---: | ---: |
| nodes | 208 | 186 | 449 | 555 | 4.7619% |
| cable length µm | 172.063042 | 159.63448 | 356.4091 | 406.892581 | 4.7619% |
| leaves | 15 | 6 | 25 | 33 | 23.8095% |
| branchpoints | 13 | 4 | 24 | 30 | 23.8095% |
| bbox X µm | 66.56 | 12.8 | 35.84 | 88.064 | 90.4762% |
| bbox Y µm | 39.936 | 36.864 | 69.12 | 79.36 | 4.7619% |
| bbox Z µm | 33.792 | 30.72 | 119.808 | 168.96 | 4.7619% |

The target is descriptively shorter/sparser and narrower in Y/Z than the peer median while spanning farther in X. **No biological class conclusion is drawn from these simple metrics.**

## Frozen verification rule

The discovery audit remains threshold-free. `proprioception_morphology_receipt.py` injects only the exact frozen receipt SHA and raw target SWC SHA. Any change in official skeleton bytes, selected population, or derived geometry fails closed.

This receipt is a reproducibility lock, not a morphology classification cutoff.

## Hard locks

Even a reproducible morphology receipt must keep:

- `promotion_ready=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `current_calibration_authorized=false`
- `direction_tuning_resolved=false`

A green frozen receipt means **REVIEW_REQUIRED**, not promotion.

## What this evidence cannot prove

Simple centerline metrics do not establish that body `905407` is biologically equivalent to every other hook neuron, nor do they resolve whether `SNpp39` or `SNpp41` corresponds to extension vs flexion tuning.

If stronger morphology classification is needed after this receipt is frozen, use an explicit shape-comparison method such as a registered-space/NBLAST-style analysis as a separate evidence gate rather than inventing a cutoff here.
