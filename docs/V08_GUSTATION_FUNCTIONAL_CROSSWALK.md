# V0.8 — Gustation functional crosswalk v0.1

Status: **evidence-backed functional mapping audit; stimulation still disabled**

The initial prepared-MaleCNS gustation audit found 1,428 curator-labelled first-order gustatory sensory neurons, but the pinned MaleCNS annotation table did not itself assign sugar, bitter, water, or salt function to most of them.

NeuroFly therefore adds only a small crosswalk supported by explicit curated cross-dataset evidence. Unresolved types stay unresolved.

## Authoritative context

Tastekin et al., *Cell* (2026), `The complete gustatory connectome of adult Drosophila reveals how taste guides feeding, foraging, and social behavior`, reports a complete male adult gustatory connectome and explicitly describes GRN diversity through molecular-identity mapping.

Virtual Fly Brain (VFB) provides queryable curated neuron ontology/classification pages and cross-dataset type relations that can be used to connect exact MaleCNS types with functional FlyWire gustatory subclasses where the mapping is unambiguous.

## Accepted v0.1 mappings

### `LB1b` → `bitter`

Accepted because:

- VFB directly classifies an individual MaleCNS `LB1b` neuron (`LB1b_R`, MaleCNS:522752) as a **bitter-sensing neuron**;
- VFB/FlyWire also labels type `LB1b` with curated gustatory subclass `bitter`.

This is the strongest mapping in v0.1 because it has both direct MaleCNS functional classification and cross-dataset agreement.

### `LB3a`, `LB3b`, `LB3c`, `LB3d` → `sugar_water`

Accepted only as the combined functional class `sugar_water`, not as pure sugar.

VFB MaleCNS pages cross-match these MaleCNS types to FlyWire type `LB3`. VFB/FlyWire classifies `LB3` as gustatory subclass `sugar/water`.

NeuroFly must therefore preserve the ambiguity. It may say these MaleCNS types are mapped to a **combined sugar/water class**, but it must not choose sugar versus water without additional evidence.

## Explicitly unresolved examples

### `LB1a`

FlyWire has `LB1a` bitter examples, but the MaleCNS VFB cross-match exposed in this evidence pass is `flywireType = LB1a,LB1d`. That cross-match is ambiguous, so NeuroFly does not promote `LB1a` to bitter in the MaleCNS runtime yet.

### `LB1c`

MaleCNS has a clean `flywireType = LB1c` relation, but this evidence pass did not verify an explicit functional FlyWire/VFB subclass for `LB1c`. It stays unresolved.

### `LB1d`

Shares the ambiguous `LB1a,LB1d` cross-match and remains unresolved.

All other gustatory neurons from the 1,428-neuron discovery set remain unresolved unless separately evidenced.

## Machine-readable source

`data/gustation_functional_crosswalk_v01.json`

Every mapping stores:

- exact MaleCNS type;
- functional class;
- confidence boundary;
- evidence URLs;
- `stimulation_authorized: false`.

The crosswalk itself also keeps `stimulation_enabled: false`.

## Prepared-MaleCNS audit gate

Run:

```bash
python -m neurofly.gustation_crosswalk_audit \
  --output runs/gustation/gustation-functional-crosswalk-audit.json
```

The audit requires:

- every mapped MaleCNS type exists in the pinned prepared dataset;
- mapped rows are curator-classified `gustatory`;
- no mapped type silently disappears;
- unresolved gustatory neurons remain counted as unresolved;
- stimulation remains disabled.

## What PASS would mean

PASS means:

> the small evidence-backed functional crosswalk resolves to real first-order gustatory neurons in NeuroFly's exact pinned MaleCNS dataset.

PASS does **not** mean:

- the full 1,428-neuron gustatory population is functionally classified;
- `sugar_water` has been separated into sugar and water;
- gustatory current is calibrated;
- food contact is already connected to these neurons;
- bitter or sugar taste improves behavior;
- NeuroFly has a biologically complete taste system.

## Next gate after PASS

If the prepared audit passes, design a **contact-only gustatory transduction contract** while keeping neural stimulation disabled. The environment may report only a local tastant class/intensity at physical contact, never food coordinates, reward value, path, target, or an already-solved `edible` decision.
