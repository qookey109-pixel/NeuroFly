# V1 FeCO Hook Cross-Dataset Identity Guard

Status: **EVIDENCE CROSSCHECK ONLY — POLARITY GATE REMAINS LOCKED**

This audit addresses a subtle but important failure mode in the unresolved
`SNpp39` / `SNpp41` polarity problem:

> identical systematic type labels across MANC and MaleCNS must not be assumed
> to mean identical biological subclass identity.

## Current MaleCNS state

Current MaleCNS VFB records classify representative `SNpp39` and `SNpp41`
bodies as **femoral chordotonal hook neurons**.

Examples:

- MaleCNS:833439 — `SNpp39` — femoral chordotonal hook neuron
- MaleCNS:819559 — `SNpp41` — femoral chordotonal hook neuron

This agrees with the current MaleCNS Cell Type Explorer and the FlyBase
`FBbt:00049558` parent mapping already audited in PR #115.

## MANC same-name counterexamples

VFB exposes MANC bodies with the same systematic labels but different FeCO
subclass/classification assignments.

Examples:

- MANC:44595 — systematic type `SNpp39`
  - MANC subclass: metathoracic leg FeCO **club**
  - VFB classification: femoral chordotonal **club** neuron

- MANC:177398 — systematic type `SNpp41`
  - MANC subclass: mesothoracic leg FeCO **claw**
  - VFB classification: femoral chordotonal **claw** neuron

There is also an internally inconsistent MANC/VFB record:

- MANC:36039 — systematic type `SNpp41`
  - MANC subclass text: metathoracic leg FeCO **hook**
  - VFB classification: femoral chordotonal **claw** neuron

This record is especially important: even within a single public record, the
displayed subclass and ontology classification do not agree.

## Consequence

A bare statement such as:

`MANC SNpp41 == MaleCNS SNpp41`

is not sufficient evidence for carrying biological subclass or directional
polarity across datasets.

Therefore NeuroFly must reject all polarity arguments that rely only on
systematic-type string equality across MANC and MaleCNS.

This does **not** invalidate PR #113's signed-circuit candidate. It only prevents
that MANC evidence from being silently upgraded to a direct MaleCNS
type-to-polarity annotation.

The candidate remains:

- `SNpp39 -> hook extension candidate`
- `SNpp41 -> hook flexion candidate`

## NeuronBridge becomes the preferred bridge

NeuronBridge is the correct remaining route because Janelia currently exposes
both:

- FlyEM Male CNS
- FlyEM MANC

and its published open-data model supports dataset-qualified EM bodies,
driver-line metadata, and precomputed morphology matches.

The documented API includes:

- `<VER>/metadata/by_body/<body_id>.json`
- `<VER>/metadata/by_line/<line_id>.json`
- `<VER>/metadata/cdsresults/<image_id>.json`

The web client and official Python client both use these object classes for
body/line lookup and match retrieval.

## Required evidence standard

A future polarity unlock must preserve, at minimum:

1. the polarity-verified driver or LM image identity;
2. the matched **current MaleCNS** body ID;
3. the MaleCNS systematic type (`SNpp39` or `SNpp41`);
4. the match algorithm / score / metadata needed to audit the match;
5. the dataset version.

A MANC same-name type is not a substitute for this body-level bridge.

## Governance

The following are now explicit:

- `cross_dataset_same_name_inference_authorized = false`
- `body_level_mapping_required = true`
- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- `current_calibration_authorized = false`
- `runtime_stimulation_authorized = false`
- `privileged_state_bypass_authorized = false`

Machine-readable state:

`data/feco_hook_cross_dataset_identity_guard_v01.json`
