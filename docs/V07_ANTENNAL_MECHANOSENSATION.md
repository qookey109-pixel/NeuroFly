# V0.7 — Antennal mechanosensation / airflow

Status: **engineering proxy; annotation gate + frozen current-routing calibration verified; live MaleCNS stimulation still disabled**

NeuroFly's sensory policy is that the agent receives fly-accessible transduction rather than privileged world truth. V0.7 extends that rule from vision and olfaction to antennal mechanosensation.

## Biological basis

Drosophila Johnston's organ (JO) is the antennal mechanosensory organ. Published physiology divides its primary sensory neurons into several response groups. At a coarse family level:

- JO-A / JO-B are strongly associated with vibration / near-field sound;
- JO-C / JO-E contain tonic antennal-deflection responses used in wind/gravity sensing;
- anterior versus posterior antennal deflection recruits opponent C/E channels;
- bilateral antennal input contributes to directional wind sensing.

MaleCNS v1.0 contains curated `JO-C*` and `JO-E*` cell types, including examples such as `JO-CA1` and `JO-EV3`. NeuroFly therefore does not invent a synthetic neuron family name for this modality.

These facts justify testing JO-C/JO-E as **candidate** wind-sensitive input families. They do not establish that every subtype has identical tuning or that NeuroFly's simplified antennal mechanics is biologically exact.

## Engineering transduction — `neurofly-antennal-mechanosensation-v0.1`

The environment may define an airflow vector in world coordinates. That vector is never passed directly to the nervous system.

```text
world airflow vector
      ↓
fly-heading transform
      ↓
coarse left/right antennal deflection
      ↓
opponent JO-C / JO-E activation proxy
      ↓
strict sensory contract
```

The neural-eligible JSON exposes only four bounded values:

```json
{
  "left":  {"jo_c": 0.0, "jo_e": 0.7},
  "right": {"jo_c": 0.3, "jo_e": 0.0}
}
```

Exact world airflow, body-frame vector components and signed deflection remain human-only diagnostics. The sensory privilege guard rejects those fields if they accidentally enter `agent_input`.

If an environment has no airflow field, mechanosensation is explicitly unavailable; NeuroFly does not fabricate a zero-wind biological observation.

## Current proxy assumptions

V0.1 uses a deliberately simple mapping:

- posterior deflection → JO-E proxy;
- anterior deflection → JO-C proxy;
- headwind produces a bilateral response;
- crosswind differentially loads the two antennae and creates opponent left/right activation.

This is a testable engineering approximation. It is **not** a validated biomechanical model of the arista/pedicel/Johnston's-organ system.

## MaleCNS annotation gate — verified

Run:

```bash
python -m neurofly mechanosensation-audit \
  --output runs/free-malecns/mechanosensation-annotation-audit.json
```

The audit uses the exact pinned Stonkfly/MaleCNS annotation table and dynamically discovers curated types beginning with `JO-C` or `JO-E`.

Laterality policy:

1. use curated `somaSide` when present;
2. otherwise use only a curated `_L` / `_R` instance suffix;
3. never infer side from body ID, coordinates or morphology.

The prepared MaleCNS v1.0 evidence run verified:

- JO-C: 68 total = 46 left + 22 right, 0 unresolved;
- JO-E: 267 total = 157 left + 110 right, 0 unresolved;
- retained graph: 166,700 neurons / 25,582,938 directed edges.

This establishes candidate annotation availability only.

## Frozen current-routing calibration — verified

The first full calibration at engineering current `8.0` was intentionally preserved as a FAIL because all four crosswind gates were subthreshold. See [`experiments/V07_MECHANOSENSATION_CALIBRATION_ATTEMPT_1.md`](experiments/V07_MECHANOSENSATION_CALIBRATION_ATTEMPT_1.md).

A subsequent predeclared current sweep tested `8.0`, `10.0`, `12.0`, and `16.0` with a fixed policy: select the **lowest** current at which all eight frozen-weight response gates pass.

Result:

- 8.0 → 4/8 gates, FAIL;
- **10.0 → 8/8 gates, PASS and selected**;
- 12.0 → 8/8 gates, PASS;
- 16.0 → 8/8 gates, PASS.

At selected current `10.0`, the expected headwind/tailwind bilateral populations were active above baseline and both left/right crosswind conditions produced the predeclared opponent side selectivity. The selected calibration receipt is:

`b3a84b5c46e97a461d4dea0673a7db216f1c810486a8d7044020c7d4d85b52cd`

Full frozen evidence is recorded in [`experiments/V07_MECHANOSENSATION_CURRENT_SWEEP.md`](experiments/V07_MECHANOSENSATION_CURRENT_SWEEP.md).

This verifies the **engineering current-routing behavior** under matched frozen weights. It does not biologically calibrate the current or validate natural antennal biomechanics.

## Deliberate integration sequence

The required order is:

1. ✅ **Transduction contract** — world airflow becomes bounded bilateral JO-C/E proxy channels.
2. ✅ **Annotation audit** — exact MaleCNS JO-C/JO-E candidate populations are bilaterally resolvable.
3. ✅ **Frozen-weight calibration** — matched airflow-off/headwind/tailwind/crosswind routing passes at the selected engineering current 10.0.
4. **Opt-in runtime integration** — next step; disabled by default and allowed to consume only strict sensory-contract JO-C/E channels.
5. **Controlled behavioral comparison** — wind-on versus wind-off with fixed seeds and held-out evaluation before any behavioral-benefit claim.
6. **Live curriculum consideration** — only after controlled evidence; not part of current V0.7 evidence.

Existing live curriculum semantics remain unchanged.

## Scientific boundary

NeuroFly may now say:

> `JO-C*` / `JO-E*` are anatomically present candidate MaleCNS pathways, and the current engineered airflow-to-antennal-deflection adapter has a reproducible frozen-weight current-routing calibration in the pinned MaleCNS runtime.

It should **not** say:

> NeuroFly has a biologically validated fruit-fly wind sense.

That stronger statement would still require better antennal transduction validation plus controlled behavioral evidence.
