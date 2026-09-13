# V0.7 — Mechanosensation runtime opt-in

Status: **runtime plumbing only; disabled by default; live curriculum unchanged**

This phase turns the already-audited and frozen-calibrated JO-C/JO-E engineering pathway into an explicit opt-in `MaleCNSBrain` input. It does not enable wind stimulation in the normal NeuroFly curriculum.

## Default-off rule

`MaleCNSBrain` now accepts:

```python
mechanosensation_current=0.0
```

The default is `0.0`, which means no JO-C/JO-E mechanosensory current is built or delivered.

The only nonzero value accepted by the runtime is the evidence-selected engineering current:

```text
10.0
```

Other positive values, including the previously tested `8.0`, `12.0`, and `16.0`, are rejected by the runtime API. The selected value is tied to frozen-calibration receipt:

`b3a84b5c46e97a461d4dea0673a7db216f1c810486a8d7044020c7d4d85b52cd`

This is an engineering governance constraint, not a claim that `10.0` is a biological antennal current.

## Strict neural input only

The runtime does **not** accept a world airflow vector. It consumes only the strict sensory-contract payload:

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

When enabled, the four bounded values are routed to the exact retained MaleCNS candidate populations:

- left JO-C;
- right JO-C;
- left JO-E;
- right JO-E.

The population resolver uses the same annotation policy as the evidence audit: curated `somaSide`, then curated `_L` / `_R` instance suffix; no body-ID or geometric inference.

## Runtime telemetry

The opt-in path reports:

- whether runtime mechanosensation is enabled;
- selected external engineering current;
- calibration receipt SHA;
- strict four-channel input levels;
- JO-C/JO-E population spike counts;
- annotation report;
- explicit `biological_validation: false`;
- explicit `behavioral_benefit_validated: false`.

This lets later experiments distinguish "the pathway was enabled and active" from "the pathway improved behavior".

## Prepared MaleCNS runtime smoke

The branch includes `.github/workflows/mechanosensation-runtime-smoke.yml`.

The smoke test:

1. restores/verifies the pinned prepared MaleCNS graph;
2. creates a deterministic Maze environment;
3. converts a right crosswind through the strict sensory contract;
4. confirms neural input contains only `left/right × JO-C/JO-E` channels;
5. instantiates `MaleCNSBrain` with the calibrated `10.0` opt-in current;
6. executes one full `decide()` path with `learning=False`;
7. requires targeted JO-C-left and JO-E-right populations to spike;
8. requires the memory SHA to remain unchanged;
9. writes a compact receipt;
10. does not save a brain checkpoint or mutate live training state.

## Explicit non-goals

This phase does **not**:

- enable mechanosensation in `CurriculumTraining`;
- alter reward schedules;
- alter the DNp20 / DNpe017 movement decoder;
- alter anti-stall logic;
- claim natural antennal biomechanics are validated;
- claim learned wind navigation;
- claim mechanosensation improves game performance.

## Next evidence gate

After the prepared runtime smoke passes, the next phase must be a separate controlled behavior experiment:

```text
same seeds / same starting state
         ├── wind OFF
         └── wind ON (calibrated opt-in)
```

Evaluation should preserve raw MaleCNS actions separately from engineered applied actions and use held-out evaluation before any behavioral-benefit or live-curriculum claim.
