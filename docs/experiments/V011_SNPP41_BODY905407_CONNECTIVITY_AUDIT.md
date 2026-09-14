# V0.11 SNpp41 Body 905407 Connectivity Audit

Status: discovery/review evidence gate only. No proprioceptive stimulation, current calibration, tuning identity, or promotion.

## Question

PR #49 froze the single mixed-subclass SNpp41 exception in pinned MaleCNS v1.0 as:

- body ID `905407`
- type `SNpp41`
- class `mechanosensory_proprioceptive`
- subclass `leg`
- superclass `vnc_sensory`
- blank `instance`
- blank `somaSide`

The next safe question is narrower than morphology:

> Does body 905407 have a reproducible synaptic-contact connectivity fingerprint relative to the 21 SNpp41 rows annotated as `chordotonal organ`?

This experiment does **not** claim that connectivity similarity proves anatomical morphology, sensory tuning, or biological function.

## Why raw contact counts are used

Stonkfly preserves the released MaleCNS edges in `normalized/edges.arrow` with `synapse_count`. Its runtime `graph.npz` later converts those counts into signed simulation weights by multiplying by neurotransmitter sign and a model scale.

This audit therefore reads `normalized/edges.arrow` directly. It does not use runtime current weights as anatomy.

## Population

The prepared audit requires exactly:

- target: body `905407`, `SNpp41`, `mechanosensory_proprioceptive / leg`;
- peers: exactly 21 retained `SNpp41`, `mechanosensory_proprioceptive / chordotonal organ` rows.

Any missing/extra peer or target taxonomy drift fails closed.

## Connectivity fingerprint

For the target and each peer, all released retained edges are aggregated by partner taxonomy. Partner labels prefer, in order:

1. `type`
2. `subclass`
3. `class`
4. `superclass`
5. `unannotated`

Incoming and outgoing contact-count profiles remain separate. The audit records:

- total incoming/outgoing contacts;
- number of partner taxonomy groups;
- top incoming/outgoing partner groups;
- target-to-peer incoming cosine similarity;
- target-to-peer outgoing cosine similarity;
- combined direction-aware cosine similarity;
- each peer's leave-one-out median similarity to the other 20 peers;
- the target median similarity and its descriptive percentile among peer medians.

The percentile is descriptive evidence only. There is deliberately no promotion threshold such as `>0.8` or `top 10%`.

## Discovery-first receipt

The first prepared run intentionally starts with no expected connectivity digest. If the population structure is correct, it:

1. computes the complete deterministic connectivity receipt;
2. hashes the canonical JSON payload with SHA256;
3. writes and uploads the receipt artifact;
4. reports `DISCOVERY_REQUIRED` and exits non-zero.

A later evidence commit may freeze that exact SHA256 only after reviewing the observed result. This prevents post-hoc threshold selection and prevents the gate from silently accepting a changed dataset/profile.

After freezing, a green prepared run may report only `REVIEW_REQUIRED`. It must still keep:

- `promotion_ready=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `current_calibration_authorized=false`
- `morphology_evidence_present=false`

## Interpretation boundary

A reproducible connectivity receipt can answer whether body 905407's released partner-type contact pattern is stable and how it compares descriptively with other SNpp41 rows.

It cannot by itself establish:

- hook extension vs flexion tuning;
- a corrected subclass annotation;
- soma laterality;
- anatomical morphology;
- mechanotransduction gain;
- injected current amplitude;
- behavioral meaning;
- promotion for neural stimulation.

Morphology requires independent skeleton/mesh or equivalent anatomical evidence. Sensory tuning requires direct biological evidence linking the systematic type to the measured tuning identity.

## Next evidence after this gate

If the frozen connectivity receipt reproduces, investigate body `905407` with independent MaleCNS skeleton/mesh resources and compare its anatomical trajectory with the 21 chordotonal SNpp41 neurons. Keep that evidence separate from connectivity statistics.
