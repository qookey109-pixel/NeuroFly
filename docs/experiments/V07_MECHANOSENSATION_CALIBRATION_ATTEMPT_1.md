# V0.7 Mechanosensation Calibration — Attempt 1

Status: **FAIL preserved as calibration evidence**

This document freezes the first full prepared-MaleCNS frozen-weight mechanosensation calibration. The failure is intentional evidence and must not be rewritten as a pass.

## Authority

- PR: `#29 — V0.7 antennal mechanosensation — fly-relative JO-C/E wind proxy`
- Branch head tested: `1485bd177a1016253b243fed1c6141261a1c3efc`
- GitHub Actions run: `34764983743`
- Workflow: `NeuroFly Mechanosensation Evidence`
- Artifact: `neurofly-mechanosensation-evidence-34764983743-1`
- Artifact ID: `10320230697`
- Artifact ZIP SHA-256: `b911dd5cca1087da0823088ebeab4c14d89610dc7529dad0c7d9bbc657894ddd`
- Calibration receipt SHA-256: `390c33dcb7eb107429cecf0483b3334529588735ff370b347f54eb516e042bda`
- Stonkfly pin: `78ef3e05ab0fa086032098558d893667068944a0`
- Prepared graph: MaleCNS v1.0, 166,700 neurons, 25,582,938 directed edges

## Annotation gate

The exact prepared graph was scanned before stimulation.

| Family | Total | Left | Right | Unresolved |
| --- | ---: | ---: | ---: | ---: |
| JO-C | 68 | 46 | 22 | 0 |
| JO-E | 267 | 157 | 110 | 0 |

The annotation gate passed. Laterality was resolved by the predeclared `somaSide_then_curated_instance_suffix` policy, with no geometry/body-ID inference.

## Frozen calibration configuration

- plasticity: frozen
- matched baseline checkpoint: required for every condition
- neural duration: `200 ms`
- maximum mechanosensation current: `8.0`
- crosswind gain in the transduction proxy: `0.70`
- runtime stimulation: **disabled**

Conditions:

1. airflow off
2. headwind
3. tailwind
4. right crosswind
5. left crosswind

## Result

Headwind and tailwind gates passed when the transduced channel amplitude was 1.0 and therefore the injected current was 8.0.

| Gate | Baseline spikes/neuron | Stimulated spikes/neuron | Result |
| --- | ---: | ---: | --- |
| headwind → JO-E left | 0.0 | 2.5605 | PASS |
| headwind → JO-E right | 0.0 | 2.5000 | PASS |
| tailwind → JO-C left | 0.0 | 3.8261 | PASS |
| tailwind → JO-C right | 0.0 | 4.0000 | PASS |

All four crosswind gates failed. With the v0.1 transduction's `0.70` crosswind gain, a maximum current of 8.0 becomes `5.6` at the targeted crosswind channel. At that amplitude the targeted JO-C/JO-E groups emitted zero spikes in this calibration state.

| Crosswind gate | Stimulated spikes/neuron | Result |
| --- | ---: | --- |
| right crosswind → JO-C left | 0.0 | FAIL |
| right crosswind → JO-E right | 0.0 | FAIL |
| left crosswind → JO-C right | 0.0 | FAIL |
| left crosswind → JO-E left | 0.0 | FAIL |

Overall: **FAIL**.

## Interpretation

This failure does **not** invalidate the MaleCNS JO-C/JO-E annotations. It shows that the first engineering current setting did not reliably transduce the weaker crosswind channels into spikes in the retained neural model.

The next step is an explicitly labeled **engineering current calibration sweep**, preserving this failed attempt. The sweep may select a current only for future controlled experiments; it is not evidence that the chosen current equals a biological antennal current or that NeuroFly has validated natural wind sensation.

No live curriculum, learning weights, reward policy, decoder, or production runtime was changed by this attempt.
