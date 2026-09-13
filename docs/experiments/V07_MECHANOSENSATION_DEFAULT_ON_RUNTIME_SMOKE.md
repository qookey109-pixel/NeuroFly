# V0.7 — Mechanosensation default-on runtime smoke

Date: 2026-09-13
Status: **PASS**
Scope: prepared MaleCNS default-on runtime routing evidence

## Authority

- Pull request: #30 — `V0.7 mechanosensation runtime — calibrated default-on`
- Tested head: `fc708d661c657937eb92301161ee7591be79a052`
- Workflow: `NeuroFly Mechanosensation Runtime Smoke`
- Workflow run: `34766145061`
- Job: `malecns-runtime-smoke`
- Prepared backend: MaleCNS v1.0
- Neurons: 166,700
- Directed edges: 25,582,938

## What this run proved

The smoke deliberately constructed `MaleCNSBrain` **without passing `mechanosensation_current`**. Therefore the tested path was the ordinary constructor default, not an opt-in override.

The default policy resolved to the frozen-calibrated engineering current `10.0`, tied to calibration receipt:

`b3a84b5c46e97a461d4dea0673a7db216f1c810486a8d7044020c7d4d85b52cd`

A deterministic right-crosswind condition was first transduced through the strict sensory contract. Neural-eligible input was:

```json
{
  "model": "neurofly-antennal-mechanosensation-v0.1",
  "available": true,
  "left":  {"jo_c": 0.7, "jo_e": 0.0},
  "right": {"jo_c": 0.0, "jo_e": 0.7}
}
```

No world airflow vector or mechanosensation diagnostics were present in the neural payload.

## Observed prepared-MaleCNS response

The full `MaleCNSBrain.decide()` path completed successfully with `learning=False`.

Observed target-population spikes:

- JO-C left: **52**
- JO-C right: **0**
- JO-E left: **0**
- JO-E right: **111**

Decoded action in this single smoke condition: `TURN_RIGHT`.

The brain memory SHA was checked before and after the decision and remained unchanged.

## Receipt

Runtime smoke receipt SHA-256:

`d3c12a4f987f6bf427ba800ea56f86ec5d47481f87e38307364c590ba43954b8`

Actions artifact:

- Artifact ID: `10321106201`
- Artifact name: `neurofly-mechanosensation-runtime-smoke-34766145061-1`
- Artifact ZIP SHA-256: `7785a78e0f8823c7ccce4bde0bbb7bf5df5e6ea9dad3f5b995608bdf474a4105`
- Retention: 3 days; this document is the permanent compact evidence record.

## Gates that passed

- prepared MaleCNS graph verified;
- default constructor enabled mechanosensation;
- default external engineering current equaled calibrated `10.0`;
- calibration receipt matched;
- `default_policy == calibrated-on-when-sensory-payload-available`;
- `switch_exposed == false`;
- strict JO-C/JO-E neural payload contained no diagnostics;
- intended JO-C-left and JO-E-right populations both spiked;
- learning remained disabled;
- memory state remained unchanged;
- workflow completed successfully and published the receipt.

## Scientific boundary

This PASS establishes that NeuroFly's calibrated mechanosensation pathway is **default-on and operational in the prepared MaleCNS runtime** when a valid fly-accessible mechanosensory payload is provided.

It does not establish:

- exact Drosophila antennal biomechanics;
- a natural biological current magnitude;
- learned wind navigation;
- behavioral benefit from wind sensing;
- a causal interpretation of the decoded `TURN_RIGHT` action.

The project decision is to continue with mechanosensation enabled and defer a public switch and formal OFF/ON ablation study until later.
