# V1 Memory Physical-State Interaction — Run 1

Status: **EXECUTION VALID / REPLICATE DIVERSITY FAILED / FROZEN**

## Run integrity

- run: `36118733181`
- scientific head: `a4f4e6ffe97e078c0dde45e09148778f6cf074af`
- artifact: `10858405420`
- artifact SHA-256: `cfab6438841d9a445188604e5b581d877c27c5de2892e24d4a7b804e7eb71890`
- receipt SHA-256: `1ee93fc228e6f68db1e5de0b03bdc8e290a58215dc2f4335be068bbf220d4255`
- source checkpoint unchanged: `74467015e04fba2eda2bdb5efb4e5ae85dd5a7262aebfb69c63a20bb94e7c214`
- all original execution/evidence gates passed

## Post-run quality audit

The four configured seeds produced different trajectory receipt digests, but
they did **not** produce four independent neural histories.

All four had:

- reward event index `66`
- changed reward edge count `1498`
- the exact same pre-event checkpoint SHA-256:
  `63ffe8afe79da8adba0510060eb56470dc59a7dad2e42fd1b1a3d073cf244e63`
- identical condition-level and terminal per-lag expression endpoints

Therefore:

**configured replicates = 4**

**effective independent neural replicates = 1**

The trajectory receipt digest is insufficient as a neural-diversity test
because recorded context contains wall-clock-derived values such as
`survival_seconds`. Those values can change the receipt digest without
changing the replay-relevant neural state.

## Descriptive result from the one unique neural trajectory

Scheduler rebuild remained exactly equivalent to intact.

A-only (`v/g + adaptation`) and B-only
(`luminance + refractory + queue`) had little upstream suppression.

The combined A+B clear produced a large non-additive reduction:

| Endpoint | Intact | A clear | B clear | A+B clear | Interaction contrast |
|---|---:|---:|---:|---:|---:|
| changed-KC active fraction | 0.346372 | 0.343474 | 0.333396 | 0.197657 | -0.132842 |
| changed-edge L1 engaged | 0.503388 | 0.500606 | 0.496261 | 0.290437 | -0.203042 |
| MBON07 state-difference fraction | 1.000000 | 1.000000 | 1.000000 | 0.571429 | -0.428571 |
| MBON07 spike-difference fraction | 0.238095 | 0.428571 | 0.238095 | 0.095238 | -0.333333 |

This is a **useful hypothesis signal**, not a replicated mechanistic result.

## Scientific conclusion

Run 1 supports carrying forward the hypothesis that the broad-clear effect is
non-additive across physical-state subsystems. It does **not** establish that
interaction across independent neural trajectories.

No carrier, causal-learning or behavioral-promotion claim is opened.

## Recovery rule

The next study must use an outcome-blind neural-diversity gate **before**
memory-expression conditions are evaluated:

1. enumerate a preregistered candidate seed pool in fixed order;
2. record only acquisition trajectory and pre-event checkpoint;
3. accept a candidate only when its pre-event checkpoint digest is unique
   among already accepted candidates;
4. select the first four eligible candidates;
5. freeze those four selected seeds;
6. only then execute intact / scheduler / A / B / A+B expression conditions.

No expression endpoint may influence seed acceptance.

## Governance

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
