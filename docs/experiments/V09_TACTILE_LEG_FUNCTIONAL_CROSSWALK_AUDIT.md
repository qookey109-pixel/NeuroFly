# V0.9 Tactile Leg Functional Crosswalk Audit Evidence

Status: **PASS — active candidate v0.2**

This record permanently freezes the evidence chain for narrowing the pinned MaleCNS tactile annotation population into a conservative leg-associated external-touch candidate population. It also preserves the rejected v0.1 candidate and the reason it failed.

No tactile current or normal-runtime tactile transduction is authorized by this evidence stage.

## Authority

- Repository: `qookey109-pixel/NeuroFly`
- Pull request: `#38 — V0.9 tactile — evidence-backed leg contact crosswalk`
- Branch: `feature/v0.9-tactile-leg-crosswalk`
- Audited head: `dceb3e692caba3be46910aa3c8f1aa027055b2d8`
- Prepared workflow: `NeuroFly Tactile Leg Functional Crosswalk Audit`
- PASS run: `34796744730`
- PASS job: `103831251604`
- General CI run: `34796744768` — 5/5 PASS
- MaleCNS release: `MaleCNS v1.0`
- Retained neurons scanned: `166700`
- Directed edges: `25582938`
- Pinned Stonkfly commit: `78ef3e05ab0fa086032098558d893667068944a0`

## Upstream tactile population

The preceding V0.9 somatosensation annotation audit established:

- exact `mechanosensory_tactile`: **2,558 neurons**
- exact `mechanosensory_proprioceptive`: **1,454 neurons**
- broad `mechanosensory`: context-only, excluded from this pathway

The 2,558 tactile neurons are too broad to stimulate as one contact channel because they span leg, notum, wing, and generic mechanosensory-bristle annotations.

## Rejected candidate v0.1

The first evidence ledger, preserved at:

`data/tactile_leg_functional_crosswalk_v01.json`

contained eight exact type labels:

- `SNta20`
- `SNta26`
- `SNta27`
- `SNta28`
- `SNta30`
- `SNta34`
- `SNta37`
- `SNta42`

The prepared audit selected 719 exact tactile rows but **failed closed** because two mapped type names also occurred in retained rows outside the exact `mechanosensory_tactile` class:

- `SNta30`: 11 rows with `class=unknown_sensory`, `subclass=mechanosensory bristle`, `superclass=vnc_sensory`
- `SNta42`: 2 rows with `class=unknown_sensory`, `subclass=mechanosensory bristle`, `superclass=vnc_sensory`

The class gate was not relaxed. `SNta30` and `SNta42` were removed instead.

This failed v0.1 is retained as negative evidence rather than overwritten.

## Active candidate v0.2

The active evidence ledger is:

`data/tactile_leg_functional_crosswalk_v02.json`

It contains six exact single type labels:

- `SNta20`
- `SNta26`
- `SNta27`
- `SNta28`
- `SNta34`
- `SNta37`

Each type has explicit external MaleCNS / Virtual Fly Brain anatomical evidence linking an exact record to an adult leg nerve. A pinned MaleCNS row is selectable only when:

1. `class == mechanosensory_tactile`;
2. `type` exactly equals one of the six approved single labels;
3. `subclass` is exactly `leg` or `mechanosensory bristle`.

Same-name rows outside the tactile class remain a hard failure. Mapped rows in notum, wing, or any other unexpected subclass also remain a hard failure.

## Exact PASS result

Prepared MaleCNS run `34796744730` scanned all **166,700** retained neurons and selected exactly **590** conservative leg-touch candidates.

| Exact type | Selected neurons |
| --- | ---: |
| `SNta20` | 156 |
| `SNta26` | 31 |
| `SNta27` | 47 |
| `SNta28` | 74 |
| `SNta34` | 54 |
| `SNta37` | 228 |
| **Total** | **590** |

The remaining **1,968 / 2,558 tactile neurons** stay unresolved and unused by this crosswalk.

Selected fraction of the exact tactile population: `0.23064894`.

## Curator-subclass evidence tiers

Selected rows split into:

- `leg`: **66**
- `mechanosensory bristle`: **524**

Corresponding evidence tiers:

- `curator_leg_plus_external_nerve`: **66**
- `external_leg_nerve_plus_bristle_class`: **524**

These tiers describe evidence strength only. They do not authorize current injection or claim receptor physiology.

## Ambiguous combined labels remain unresolved

The audit explicitly preserved these related combined labels as unresolved rather than splitting them:

- `SNta19,SNta37`: 13
- `SNta20,SNta29`: 1
- `SNta27,SNta28`: 8
- `SNta28,SNta29`: 1
- `SNta28,SNta40`: 1
- `SNta28,SNta44`: 8
- `SNta31,SNta34`: 1

A token appearing inside a combined label never promotes that row into the 590-neuron population.

## PASS gates

All of the following were true on the pinned baseline:

- all six active crosswalk types present;
- all selected rows exactly `mechanosensory_tactile`;
- no active mapped type had a same-name retained row outside the tactile class;
- no active mapped type leaked into a disallowed subclass;
- combined labels remained unselected;
- selected population exactly 590;
- unresolved population preserved;
- `stimulation_enabled = false`;
- `runtime_transduction_enabled = false`.

## Artifact

- Artifact ID: `10330166200`
- Artifact name: `neurofly-tactile-leg-crosswalk-34796744730-1`
- Artifact ZIP SHA-256: `2edf03e4838a42fb4b33be86403dd87eeee36c42d6842962b9fea4f307c2a4e8`

The Actions artifact is short-lived; this document is the permanent compact evidence record.

## Scientific boundary

This PASS establishes only an evidence-backed **candidate sensory population** for a future engineering external-touch proxy.

It does not establish:

- a full six-leg biomechanical model;
- bristle/receptor transfer functions;
- natural firing rates;
- a tactile current value;
- wall, floor, food, or predator semantics inside MaleCNS;
- locomotor or navigation benefit;
- biological validation.

A later contact transducer must be generated only from a physical contact event and must not provide the agent with map geometry, wall coordinates, exact collision normals, object IDs, target labels, routes, reward, or desired actions.

Proprioception remains a separate evidence chain and must not be approximated by privileged game velocity, heading, or world displacement.
