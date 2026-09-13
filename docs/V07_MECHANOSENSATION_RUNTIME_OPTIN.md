# V0.7 — Mechanosensation runtime default-on

Status: **calibrated mechanosensation enabled by default; no public on/off switch yet**

This phase turns the already-audited and frozen-calibrated JO-C/JO-E engineering pathway into a normal `MaleCNSBrain` sensory input. NeuroFly now treats antennal mechanosensation like vision and olfaction: the sensory system is present by default whenever an environment provides a valid airflow field.

## Default-on rule

`MaleCNSBrain` now defaults to the evidence-selected engineering current:

```python
mechanosensation_current=MECHANOSENSATION_CALIBRATED_CURRENT
```

which currently resolves to:

```text
10.0
```

The selected value is tied to frozen-calibration receipt:

`b3a84b5c46e97a461d4dea0673a7db216f1c810486a8d7044020c7d4d85b52cd`

Other positive values, including the previously tested `8.0`, `12.0`, and `16.0`, are rejected by the runtime API. `0.0` remains accepted only as a low-level compatibility hook for future switch/ablation work; it is not the standard NeuroFly runtime mode and no public switch is exposed in this phase.

This is an engineering governance constraint, not a claim that `10.0` is a biological antennal current.

## Sensory availability is not the same as disabling the system

The mechanosensory pathway is default-on, but NeuroFly still refuses to invent sensory evidence. If an environment does not define airflow, the sensory contract reports the modality as unavailable and delivers no JO-C/JO-E pulse for that observation.

That means:

```text
mechanosensory system = ON by default
no airflow field       = no fabricated wind signal
valid airflow field    = transduce → JO-C/JO-E → MaleCNS
```

## Strict neural input only

The runtime does **not** accept a world airflow vector directly. It consumes only the strict sensory-contract payload:

```json
{
  "model": "neurofly-antennal-mechanosensation-v0.1",
  "available": true,
  "encoding": "bilateral-jon-c-e-deflection-proxy",
  "left":  {"jo_c": 0.7, "jo_e": 0.0},
  "right": {"jo_c": 0.0, "jo_e": 0.7}
}
```

Privileged fields such as world airflow, exact body-relative vectors, coordinates, bearing, routes, paths, or signed-deflection diagnostics are rejected before stimulation.

The four bounded values are routed to the exact retained MaleCNS candidate populations:

- left JO-C;
- right JO-C;
- left JO-E;
- right JO-E.

The population resolver uses the same annotation policy as the evidence audit: curated `somaSide`, then curated `_L` / `_R` instance suffix; no body-ID or geometric inference.

## Runtime telemetry

The default-on path reports:

- whether a valid mechanosensory observation was available;
- selected external engineering current;
- calibration receipt SHA;
- strict four-channel input levels;
- JO-C/JO-E population spike counts;
- annotation report;
- `default_policy: calibrated-on-when-sensory-payload-available`;
- `switch_exposed: false`;
- explicit `biological_validation: false`;
- explicit `behavioral_benefit_validated: false`.

## Prepared MaleCNS runtime smoke

The branch includes `.github/workflows/mechanosensation-runtime-smoke.yml`.

The smoke test:

1. restores/verifies the pinned prepared MaleCNS graph;
2. creates a deterministic Maze environment;
3. converts a right crosswind through the strict sensory contract;
4. confirms neural input contains only `left/right × JO-C/JO-E` channels;
5. instantiates `MaleCNSBrain` under the calibrated default-on policy;
6. executes one full `decide()` path with `learning=False`;
7. requires targeted JO-C-left and JO-E-right populations to spike;
8. requires the memory SHA to remain unchanged;
9. writes a compact receipt;
10. does not save a brain checkpoint or mutate live training state.

## Current project decision

NeuroFly will **not** pause here to run a wind-OFF versus wind-ON behavioral comparison. The project will continue with mechanosensation enabled as part of the normal sensory stack.

A user-facing switch and formal ablation/control experiment are deferred until later, when NeuroFly needs to quantify the marginal contribution of each sensory modality.

This changes the development order, not the scientific claim boundary: current work still must not claim that mechanosensation improves navigation or reproduces exact fruit-fly wind sensing without later controlled evidence.

## Explicit boundaries

This phase does **not**:

- expose a public mechanosensation toggle;
- alter reward schedules;
- alter the DNp20 / DNpe017 movement decoder;
- alter anti-stall logic;
- fabricate wind when an environment provides none;
- claim natural antennal biomechanics are validated;
- claim learned wind navigation;
- claim mechanosensation improves game performance.

## Next implementation direction

After the prepared default-on runtime smoke passes, continue integrating the sensory stack forward rather than building an OFF/ON experiment now. The next environment work should provide explicit, reproducible airflow fields and route them through the strict sensory contract so NeuroFly can experience wind continuously alongside vision and olfaction.
