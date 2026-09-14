# V0.11 SNpp41 Body 905407 Connectivity Audit

Status: review evidence gate only. No proprioceptive stimulation, current calibration, tuning identity, or promotion.

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

## Prepared discovery result

Prepared run `34809806467` completed the structural audit and intentionally exited non-zero with `DISCOVERY_REQUIRED` after publishing the first receipt.

Pinned prepared dataset receipt:

- retained neurons: `166700`
- directed retained edge rows: `25582938`
- retained synaptic contacts: `124177617`
- target body: `905407`
- peer count: `21`
- canonical connectivity SHA256: `353e2771de973ad638878eac9fb1f76e742f928d2cc638c45f1b50775fce2e0e`

Body `905407` contact summary:

- incoming: `56` contacts across `5` partner taxonomy groups
- outgoing: `87` contacts across `35` partner taxonomy groups

Descriptive comparison:

- target median combined cosine to the 21 peers: `0.770609350`
- peer leave-one-out median-of-medians: `0.871593249`
- peer median range: `0.237632620` to `0.899014118`
- target percentile among the 21 peer median values: `23.80952381`
- highest target-to-peer combined similarity: body `817154`, `0.827068065`

The target's incoming partner-type profile is broadly similar to many peers: for the majority of peers, incoming cosine similarity is roughly `0.88–0.97`. Its outgoing similarity is lower, generally around `0.21–0.46`. Three peers (`816362`, `826386`, `936031`) have zero incoming cosine to the target and also have unusually low leave-one-out peer similarity, showing that the annotated peer population itself is heterogeneous.

The conservative interpretation is therefore:

> Body `905407` shares substantial incoming connectivity structure with many SNpp41 chordotonal peers, while its outgoing partner distribution is more divergent. Its combined fingerprint falls in the lower part of the observed SNpp41 peer heterogeneity, but is not isolated enough to justify reclassification from connectivity alone.

This is descriptive connectivity evidence only. It does not resolve why the row is annotated `leg`, and it does not establish extension/flexion tuning.

## Frozen receipt verification

The exact prepared discovery digest is frozen in `proprioception_connectivity_receipt.py`. The discovery module itself remains threshold-free and does not contain a guessed expected digest.

The frozen SHA is a reproducibility receipt, not a biological decision threshold. A verification run succeeds only if the exact canonical connectivity payload reproduces. Any change in the target/peer population, partner taxonomy, or contact counts changes the digest and fails closed.

A green frozen verification may report only `REVIEW_REQUIRED`. It must still keep:

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
