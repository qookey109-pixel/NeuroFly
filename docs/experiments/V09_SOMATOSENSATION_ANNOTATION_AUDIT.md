# V0.9 Somatosensation Annotation Audit Evidence

Status: **PASS**

This record permanently freezes the first prepared-MaleCNS evidence for NeuroFly V0.9 tactile/proprioceptive discovery. It is an annotation audit only. No somatosensory stimulation or normal-runtime transduction was enabled by this experiment.

## Authority

- Repository: `qookey109-pixel/NeuroFly`
- Branch: `feature/v0.9-somatosensation-annotation-audit`
- Audited head: `ad0bbe1aa30d06ec4963c77475722692fea45a4f`
- Workflow: `NeuroFly Somatosensation Annotation Audit`
- Run: `34795932348`
- Job: `103828902225`
- MaleCNS release: `MaleCNS v1.0`
- Retained neurons scanned: `166700`
- Directed edges: `25582938`
- Pinned Stonkfly commit: `78ef3e05ab0fa086032098558d893667068944a0`

## Membership policy

Only exact curator annotation class membership was accepted:

- `mechanosensory_tactile` → tactile discovery population
- `mechanosensory_proprioceptive` → proprioceptive discovery population

The broad `mechanosensory` class was counted as context only and was not promoted into either population. Descriptive words in names or subclasses were not allowed to create membership.

## Exact retained counts

| Population | Exact retained neurons |
| --- | ---: |
| Tactile (`mechanosensory_tactile`) | **2,558** |
| Proprioceptive (`mechanosensory_proprioceptive`) | **1,454** |
| Total V0.9 discovery targets | **4,012** |
| Broad `mechanosensory` context-only | **1,733** |

## Tactile subclasses

| Curator subclass | Count |
| --- | ---: |
| mechanosensory bristle | 2,130 |
| leg | 213 |
| notum | 214 |
| wing | 1 |

All 2,558 tactile neurons were annotated `vnc_sensory` at the superclass level.

## Proprioceptive subclasses

| Curator subclass | Count |
| --- | ---: |
| campaniform sensilla | 426 |
| chordotonal organ | 425 |
| hair plate | 113 |
| haltere | 201 |
| leg | 190 |
| abdomen | 66 |
| wing | 19 |
| notum | 12 |
| neck | 1 |

Superclass distribution:

- `vnc_sensory`: 1,030
- `sensory_ascending`: 423
- `sensory_ascending_tbc`: 1

## Retained type examples relevant to later crosswalk work

The audit does not assign function from type names, but confirms the exact pinned graph contains many externally described tactile and proprioceptive types.

Selected retained tactile counts include:

- `SNta20`: 156
- `SNta26`: 31
- `SNta27`: 47
- `SNta28`: 74
- `SNta30`: 54
- `SNta34`: 54
- `SNta37`: 228
- `SNta42`: 75

Selected retained proprioceptive counts include:

- `SNpp39`: 39
- `SNpp40`: 32
- `SNpp50`: 62
- `SNpp51`: 31
- `SNpp58`: 16
- `SNpp59`: 6
- `SNpp60`: 41

These counts authorize only the next evidence stage: intersecting exact retained MaleCNS types with independently supported receptor/body-region identities. They do **not** authorize stimulation.

## Annotation limitations discovered

The pinned annotation frame exposed:

- `class`
- `subclass`
- `type`
- `instance`
- `somaSide`
- `superclass`

It did **not** expose a usable nerve column in this audit, so nerve/body-region assignment must not be inferred from missing data. Future crosswalks must explicitly cite external anatomical evidence and intersect it with the exact retained types above.

Combined or unresolved type labels such as `SNta02,SNta09`, `SNtaxx`, `SNxxxx`, `SNppxx`, or mixed labels remain unresolved unless a later evidence gate can classify the complete retained record safely.

## Safety / scientific gates preserved

At PASS:

- `stimulation_enabled = false`
- `runtime_transduction_enabled = false`
- existing JO-C / JO-E routing modified = false
- no tactile current was injected
- no proprioceptive current was injected
- no game coordinates, collision geometry, target labels, or reward values were added to agent input
- no decoder or learning-policy change occurred

## Artifact

- Artifact ID: `10329866840`
- Artifact name: `neurofly-somatosensation-annotation-audit-34795932348-1`
- Artifact ZIP SHA-256: `1a0bd0c90567b155878d17bba1a43c6c0c4497aa11460abb79a7f71e09db204f`

The Actions artifact is short-lived; this document is the permanent compact evidence record.

## Interpretation

This PASS establishes only that the exact pinned MaleCNS graph contains substantial curator-labelled tactile and proprioceptive sensory populations. It does not establish receptor transfer functions, body-contact geometry, joint-state encoding, engineering currents, natural firing rates, behavioral benefit, or learning benefit.

The next authorized stage is a **read-only functional crosswalk**. Tactile contact is the preferred first runtime candidate because it can later be derived from real physical contact as a transient fly-relative signal. Proprioception remains a separate problem and must not be approximated by privileged game velocity or heading vectors.
