# V0.7 — Ambient airflow normal-runtime smoke

Date: 2026-09-13
Status: **PASS**
Scope: normal curriculum ambient-airflow → strict sensory contract → default-on prepared MaleCNS runtime

## Authority

- Pull request: #31 — `V0.7 ambient airflow — keep mechanosensation active in normal curriculum`
- Tested head: `5e4bbd964a78263bec06de9fbbbfc5b3c208baf6`
- Workflow: `NeuroFly Ambient Airflow Runtime Smoke`
- Workflow run: `34766471822`
- Job: `ambient-airflow-runtime-smoke`
- Prepared backend: MaleCNS v1.0
- Neurons: 166,700
- Directed edges: 25,582,938

## What this run proved

The smoke used a normal `CurriculumMazeEnvironment(seed=109)` and consumed its ordinary `snapshot(include_grid=False)` directly as the `MaleCNSBrain` context.

No smoke-only mechanosensory payload was fabricated, and no mechanosensation-current override was supplied to `MaleCNSBrain`.

The normal curriculum reported policy:

`neurofly-curriculum-ambient-airflow-v1`

with persistence provenance world vector:

```json
{"x": 0.0, "y": 1.0}
```

The exact world vector was **not** present in the runtime brain context. For the canonical RIGHT-facing pose, the strict fly-accessible mechanosensory payload was:

```json
{
  "model": "neurofly-antennal-mechanosensation-v0.1",
  "available": true,
  "left":  {"jo_c": 0.7, "jo_e": 0.0},
  "right": {"jo_c": 0.0, "jo_e": 0.7}
}
```

The runtime used the frozen-calibrated engineering current `10.0`, tied to calibration receipt:

`b3a84b5c46e97a461d4dea0673a7db216f1c810486a8d7044020c7d4d85b52cd`

## Observed prepared-MaleCNS response

The full normal `MaleCNSBrain.decide()` path completed successfully with `learning=False`.

Observed target-population spikes:

- JO-C left: **52**
- JO-C right: **0**
- JO-E left: **0**
- JO-E right: **111**

Decoded action in this single smoke condition: `TURN_RIGHT`.

The brain memory SHA was checked before and after the decision and remained unchanged.

## Receipt

Ambient-airflow runtime smoke receipt SHA-256:

`7a46e1e04608d34884c3b43d51c7e753b599d35b46e0bc7eab3d0a266b0df76a`

Actions artifact:

- Artifact ID: `10321031793`
- Artifact name: `neurofly-ambient-airflow-runtime-smoke-34766471822-1`
- Artifact ZIP SHA-256: `76c2c1b8b8e8848990c639c94cf17ad432ceec584a648465c0ec6fd36151ff29`
- Artifact size: 795 bytes
- Retention: 3 days; this document is the permanent compact evidence record.

## Gates that passed

- prepared MaleCNS graph verified;
- normal curriculum emitted a strict mechanosensory payload;
- exact world airflow was absent from normal brain context;
- default `MaleCNSBrain` mechanosensation was enabled;
- default current equaled calibrated `10.0`;
- calibration receipt matched;
- intended JO-C-left and JO-E-right populations both spiked;
- learning remained disabled;
- memory state remained unchanged;
- persistence retained world-field provenance separately;
- general NeuroFly CI passed 5/5 on the same PR head;
- workflow completed successfully and published the receipt.

## Scientific boundary

This PASS establishes that the normal NeuroFly curriculum can continuously route a deterministic, target-independent ambient airflow through fly-relative JO-C/JO-E transduction into the prepared MaleCNS runtime.

It does not establish:

- a natural Drosophila wind speed for the normalized `1.0` field;
- exact antennal biomechanics;
- a natural biological current magnitude;
- learned wind navigation;
- behavioral benefit from mechanosensation;
- a causal interpretation of the decoded `TURN_RIGHT` action.

The project decision remains: keep mechanosensation enabled by default and defer a public switch / formal OFF-vs-ON ablation study until later.
