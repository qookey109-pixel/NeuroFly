# V0.7 — Antennal mechanosensation / airflow

Status: **engineering proxy + annotation-gated integration; live MaleCNS stimulation not yet enabled**

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

## MaleCNS annotation gate

Before any mechanosensory current is injected into MaleCNS, run:

```bash
python -m neurofly mechanosensation-audit \
  --output runs/free-malecns/mechanosensation-annotation-audit.json
```

The audit uses the exact pinned Stonkfly/MaleCNS annotation table and dynamically discovers curated types beginning with `JO-C` or `JO-E`.

Laterality policy:

1. use curated `somaSide` when present;
2. otherwise use only a curated `_L` / `_R` instance suffix;
3. never infer side from body ID, coordinates or morphology.

The audit passes only when:

- JO-C candidates exist on both left and right;
- JO-E candidates exist on both left and right;
- every candidate used by the broad family query has resolvable laterality.

A PASS still reports `stimulation_enabled: false`. It validates annotation availability only.

## Deliberate integration sequence

The required order is:

1. **Transduction contract** — world airflow becomes bounded bilateral JO-C/E proxy channels.
2. **Annotation audit** — verify exact MaleCNS candidate populations and laterality.
3. **Frozen-weight calibration** — after the audit passes, add matched conditions such as airflow-off, headwind, tailwind, left/right crosswind and measure the targeted population response without plasticity.
4. **Opt-in runtime integration** — only after calibration passes may a versioned experiment inject mechanosensory current into MaleCNS.
5. **Training comparison** — compare wind-on versus wind-off under controlled seeds and held-out evaluation before claiming behavioral benefit.

Current V0.7 work stops before step 3. Existing live curriculum semantics therefore remain unchanged.

## Scientific boundary

NeuroFly should say:

> `JO-C*` / `JO-E*` are anatomically present candidate MaleCNS pathways, and an engineered airflow-to-antennal-deflection adapter is being tested against them.

It should **not** yet say:

> NeuroFly has a biologically validated fruit-fly wind sense.

That stronger statement would require validated transduction, neural response calibration and behavioral controls.
