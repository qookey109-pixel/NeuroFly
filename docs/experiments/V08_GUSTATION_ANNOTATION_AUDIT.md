# V0.8 — Gustation annotation audit

Date: 2026-09-13
Status: **PASS for curated gustatory-sensory discovery; functional taste subtype routing NOT YET AUTHORIZED**
Scope: read-only prepared MaleCNS annotation audit

## Authority

- Pull request: #32 — `V0.8 gustation — read-only MaleCNS GRN annotation discovery`
- Tested branch head at workflow start: `0961d6b822c4a8b351f7cf7d3e055a8d8fb8730f`
- Workflow: `NeuroFly Gustation Annotation Audit`
- Workflow run: `34766730847`
- Job: `malecns-gustation-audit`
- Prepared backend: MaleCNS v1.0
- Retained neurons scanned: 166,700
- Directed edges verified by prepared backend: 25,582,938
- Pinned Stonkfly commit: `78ef3e05ab0fa086032098558d893667068944a0`

## Membership rule

A neuron was counted only when the curated annotation class was exactly:

`gustatory`

(case-insensitive, with schema aliases supported by the audit).

Taste-related words or aliases did not create membership. This prevents downstream neurons with names such as sugar- or bitter-related interneurons from being mistaken for first-order gustatory sensory neurons.

## Result

Curator-labelled gustatory sensory neurons retained in the prepared MaleCNS graph:

**1,428**

Curated anatomical subclasses:

- leg bristle: **768**
- wing bristle: **385**
- labellar bristle: **163**
- taste peg: **60**
- pharyngeal sensillum: **48**

Superclass distribution:

- `vnc_sensory`: **1,073**
- `cb_sensory`: **275**
- `sensory_ascending`: **80**

Representative curated type families include:

- labellar: `LB1a` ... `LB4b`
- leg gustatory: `LgAG*`, `LgLG*`
- pharyngeal: `PhG1a` ... `PhG16`
- wing gustatory: `WG1` ... `WG4`
- taste peg: `claw_tpGRN`, `dorsal_tpGRN`

The prepared table exposed the audit fields:

- `class`
- `subclass`
- `type`
- `instance`
- `somaSide`
- `superclass`

No curated `nerve` column/value was available through the exact retained annotation table used by this runtime audit.

## Critical limitation

The pinned MaleCNS annotation fields audited here provide strong anatomical/sensillum identity, but they do **not** directly label these 1,428 neurons as sugar, bitter, water, low-salt, or another taste quality.

The audit found only the descriptive token `taste` among the retained curated type/instance/superclass strings; it did not find a trustworthy functional sugar/bitter/water/salt crosswalk in those fields.

Therefore NeuroFly must **not** infer taste quality from names such as `LB1a`, `LgLG3`, `PhG4`, or `WG2` without an external curated mapping.

## Gate interpretation

PASS establishes only:

> the exact pinned prepared MaleCNS contains a large, curator-labelled population of first-order gustatory sensory neurons that is suitable for further mapping.

PASS does not establish:

- which exact GRNs encode sugar/sweet;
- which encode bitter/aversive taste;
- which encode water or salt-related signals;
- which current magnitude should stimulate them;
- that contact events are already connected to these cells;
- that NeuroFly has biologically validated taste.

`stimulation_enabled` remains **false**.

## Evidence artifact

- Artifact ID: `10320657913`
- Artifact name: `neurofly-gustation-annotation-audit-34766730847-1`
- Artifact ZIP SHA-256: `b00e6ec7c076d0b1981ef02c0556a27a55e7ff21942ba1a444d780076a7bc0e9`
- Artifact size: 1,709 bytes
- Retention: 3 days; this document is the permanent compact evidence record.

General NeuroFly CI on the same PR generation also passed all five jobs.

## Next gate

Before any gustatory stimulation, obtain a curated literature/dataset crosswalk from MaleCNS sensory type identity to known taste modality/receptor class where evidence exists.

The next audit must explicitly distinguish:

1. dataset-supported mappings;
2. literature-supported mappings that can be joined deterministically to MaleCNS type/sensillum identity;
3. unresolved neurons that remain unassigned.

Unresolved neurons must stay unused rather than being guessed.
