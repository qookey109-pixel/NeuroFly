# V0.10 Proprioception FeCO Functional Crosswalk Audit

Status: prepared MaleCNS evidence frozen. Read-only discovery only; no proprioceptive runtime transduction and no proprioceptive current are authorized.

## Purpose

The pinned MaleCNS v1.0 graph contains 166,700 retained neurons, including 1,454 neurons curated as `mechanosensory_proprioceptive`. Of those, 425 are curated as `subclass=chordotonal organ`.

This stage asks only which exact retained MaleCNS types can be conservatively associated with FeCO functional families while remaining unambiguous under the pinned curator annotations.

It does **not** treat game velocity, heading, world displacement, map coordinates, or desired actions as proprioception.

## Candidate v0.1 — rejected by prepared audit

The initial evidence ledger contained seven exact type labels:

- `SNpp39` — hook candidate
- `SNpp40` — club candidate
- `SNpp50` — claw candidate
- `SNpp51` — claw candidate
- `SNpp58` — club candidate
- `SNpp59` — club candidate
- `SNpp60` — club candidate

Prepared MaleCNS run `34800856439` rejected this candidate. If only the matching chordotonal-organ rows had been counted, the candidate would have selected 223 neurons, but the exact-type names were not clean enough for the fail-closed policy.

Disallowed same-type proprioceptive subclass rows were present:

- `SNpp40|leg`: 2
- `SNpp50|leg`: 1
- `SNpp51|leg`: 1

In addition, `SNpp51` had one same-name retained row outside the proprioceptive class:

- `class=unknown_sensory`
- `subclass=leg`
- `superclass=vnc_sensory`

The class/subclass gate was **not** relaxed. The rejected v0.1 ledger is preserved at:

`data/proprioception_feco_functional_crosswalk_v01.json`

This negative evidence is intentional and should not be overwritten.

## Active v0.2 — prepared PASS

The conservative active ledger keeps only four exact single type labels with clean pinned annotation intersections:

- `SNpp39` — `feco_hook_motion_direction_candidate`
- `SNpp58` — `feco_club_bidirectional_motion_vibration_candidate`
- `SNpp59` — `feco_club_bidirectional_motion_vibration_candidate`
- `SNpp60` — `feco_club_bidirectional_motion_vibration_candidate`

Active ledger:

`data/proprioception_feco_functional_crosswalk_v02.json`

Prepared MaleCNS run `34801043586`, job `103843631225`: **PASS**.

### Exact retained counts

- total MaleCNS neurons scanned: **166,700**
- `mechanosensory_proprioceptive`: **1,454**
- `chordotonal organ`: **425**
- selected conservative FeCO candidates: **102**
- unresolved proprioceptive neurons: **1,352**

Exact type counts:

- `SNpp39`: **39**
- `SNpp58`: **16**
- `SNpp59`: **6**
- `SNpp60`: **41**

Functional candidate counts:

- hook motion-direction candidate: **39**
- club bidirectional-motion / vibration candidate: **63**

Prepared v0.2 found:

- no missing active types;
- no same-name active rows outside `mechanosensory_proprioceptive`;
- no active rows outside `subclass=chordotonal organ`;
- no selected combined labels;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`.

## Claw status

FeCO claw / tibia-position remains **UNRESOLVED / REVIEW REQUIRED** for NeuroFly V0.10.

`SNpp50` and `SNpp51` have useful external FeCO-claw evidence, but their exact retained MaleCNS type labels cross annotation boundaries that fail the current conservative type-level policy. They must not be silently promoted into runtime or current calibration.

This does not mean claw neurons are biologically absent. It means the current exact-type mapping is not clean enough for NeuroFly's fail-closed runtime boundary.

## Evidence artifact

Prepared PASS artifact:

- run: `34801043586`
- job: `103843631225`
- artifact ID: `10330808794`
- artifact ZIP SHA-256: `063774b7304754e880e6005839a1bb4a4ce185e43c43adce2dd86e319079c9fb`
- Stonkfly commit: `78ef3e05ab0fa086032098558d893667068944a0`

General NeuroFly CI on the same head:

- run `34801043611`: **PASS**

## Scientific boundary

This PASS establishes only an evidence-backed annotation crosswalk for a conservative FeCO hook+club candidate subset.

It does **not** establish:

- natural receptor biomechanics;
- femur/tibia joint geometry;
- tibial position encoding;
- tibial movement direction encoding;
- vibration-to-neural transfer functions;
- proprioceptive current amplitude;
- runtime proprioception;
- behavioral benefit;
- biological validation.

## Required next stage

Before any proprioceptive current calibration, NeuroFly needs a versioned **virtual receptor-accessible leg/joint-state contract**.

That contract must create internal body/joint mechanical variables and transduce only those variables into FeCO-like channels. It must not pass world-space position, raw game velocity, heading, route information, reward, or desired action as if those were biological proprioception.

The safest first contract can support hook/club-like motion signals while claw remains unavailable until its annotation/evidence boundary is resolved.
