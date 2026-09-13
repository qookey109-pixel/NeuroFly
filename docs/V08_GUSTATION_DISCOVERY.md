# V0.8 — Gustation discovery gate

Status: **annotation discovery only; no taste stimulation enabled**

NeuroFly's gustation design follows the same sensory rule as vision, olfaction and antennal mechanosensation: the nervous system should receive only a fly-accessible sensory event, never solved world truth.

## Behavioral boundary

Taste is a contact modality in this phase.

```text
food far away
  → visual / olfactory cues may exist
  → gustation unavailable

fly physically contacts food
  → local contact event
  → gustatory transduction may become available
```

The environment must not expose food coordinates, food identity, reward value or an `edible=true` answer as gustatory neural input.

## Biological discovery target

Drosophila gustatory receptor neurons (GRNs) include modality groups associated with sugar/sweet, bitter, water and salt-related sensing, among others. Their primary sensory axons project into subesophageal / gnathal regions before taste information reaches downstream interneurons.

For MaleCNS integration, NeuroFly does **not** infer a GRN from a taste-related neuron alias. A downstream neuron can be described as sugar- or bitter-related without being a first-order gustatory sensory neuron.

The first gate therefore uses only the exact pinned MaleCNS curator annotation class:

`class == gustatory`

(case-insensitive, with supported schema aliases only).

## Read-only annotation audit

Run:

```bash
python -m neurofly.gustation_audit \
  --output runs/gustation/gustation-annotation-audit.json
```

The audit reports:

- number of curated gustatory sensory neurons;
- subtype / subclass values when available;
- nerve annotations when available;
- curated type and instance distributions;
- soma-side distribution;
- superclass distribution;
- descriptive taste/receptor tokens as metadata only.

Taste words or receptor names **never create membership**. They are diagnostic descriptions after a neuron has already passed the curated gustatory-class gate.

## Gate semantics

PASS means only:

> the exact pinned prepared MaleCNS annotations contain curator-labelled gustatory sensory neurons that can be studied further.

PASS does **not** mean:

- sugar and bitter populations are already safely separated;
- taste current has been calibrated;
- contact events are already connected to MaleCNS;
- a food reward should be injected directly into GRNs;
- NeuroFly has biologically validated taste.

Every audit report therefore keeps:

`stimulation_enabled: false`

## Planned sequence after discovery

If the audit identifies trustworthy subtype structure, the next order is:

1. subtype audit for candidate appetitive/aversive GRN populations;
2. contact-only gustatory transduction contract;
3. frozen-weight stimulation calibration;
4. prepared-MaleCNS isolated runtime smoke;
5. normal environment integration where gustation exists only during physical contact.

If the annotation table does not provide enough subtype resolution, NeuroFly should stop at discovery and seek an external curated crosswalk rather than inventing sugar/bitter identities.
