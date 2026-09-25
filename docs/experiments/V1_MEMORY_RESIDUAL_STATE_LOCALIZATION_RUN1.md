# V1 Reward Memory Residual-State Localization — Run 1

## Status

**EXPLORATORY MEMORY RESIDUAL-STATE LOCALIZATION COMPLETE**

Successful run: `36113626269`

- scientific head: `696d1d94d2ff53141d07a8c9e58795ec7ab4ad5c`
- artifact: `10854912760`
- artifact digest: `sha256:60656077fbc0282fabc1535087c4987577474a4aea88b189c8ef85dfc757a292`
- receipt digest: `9a0c9595ef53824690ebac0f661e04ff3b0803f78a2052905c4a5641bf4f55d6`
- source checkpoint unchanged: `c9d7cdcee82b97042360d2c63b24876e515774e9d69624585e38cf49d29d91e3`

All preregistration and intervention-purity gates passed.

## Aggregate result

| condition | KC coverage | MBON state | MBON spike | action | cue action | KC mean | L1 mean | MBON-state mean | action mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| intact | 3/4 | 3/4 | 3/4 | 2/4 | 0/4 | 0.239526 | 0.358375 | 0.726190 | 0.023810 |
| clear kernel credit | 3/4 | 3/4 | 3/4 | 2/4 | 0/4 | 0.239526 | 0.358375 | 0.726190 | 0.023810 |
| clear luminance | 4/4 | 4/4 | 4/4 | 3/4 | 1/4 | 0.311359 | 0.468582 | 0.964286 | 0.059524 |
| clear refractory/delay | 4/4 | 4/4 | 3/4 | 3/4 | 1/4 | 0.236642 | 0.357292 | 0.714286 | 0.119048 |
| clear adaptation | 4/4 | 4/4 | 3/4 | 2/4 | 0/4 | 0.203140 | 0.297823 | 0.571429 | 0.059524 |

## Kernel credit state is excluded

Clearing:

- `eligibility`
- `eligibility_last`
- `modulation`
- `modulation_last`

was **exactly identical to intact** on every stored aggregate and every
terminal per-lag endpoint.

This state class therefore does not carry the already-stored frozen-recall
expression in this assay.

## Luminance is not the positive carrier

Clearing retinal `luminance` increased expression substantially and recovered
the previously silent RL1 trajectory.

That direction is inconsistent with luminance being the positive state carrying
the 3 tau benefit. It is better described here as an input-state / suppressive
modulator.

## Refractory / pending-delay state is mixed

Clearing `refractory / queue / queue_count` barely changed aggregate KC/L1
density, slightly reduced MBON-state/spike density, but increased action
divergence and recovered RL1.

This is not a clean loss-of-expression result, so the state class is not a
confirmed positive carrier.

## Adaptation is mechanistically relevant but heterogeneous

Adaptation produced the only substantial aggregate reduction in neural
expression density:

- changed-KC mean: `0.239526 → 0.203140`
- changed-edge L1 mean: `0.358375 → 0.297823`
- MBON-state fraction: `0.726190 → 0.571429`

But the effect is not consistent enough for a carrier claim:

- RL3 showed a strong collapse in KC/L1/MBON-state density;
- RL1 was silent intact and gained expression after adaptation clearing;
- RL2 and RL4 remained close to intact on neural density;
- action-divergence density increased overall rather than decreasing.

Therefore adaptation remains a **mixed expression-modulator candidate**, not a
confirmed positive carrier.

## Updated localization

The state space is now much smaller:

- centered `rate_kc/rate_dan`: excluded;
- kernel eligibility/modulation: excluded;
- wrapper visual history: excluded;
- luminance: suppressive/input modulator;
- `v/g`: strong modulator, clearing enhances expression;
- refractory/pending delay: mixed dynamics modulator;
- adaptation: mixed, trajectory-dependent modulator.

The remaining unresolved mechanism is concentrated in the deferred
lazy-integration scheduler state and possible interactions among that scheduler,
adaptation and membrane/conductance state.

## Next study

Do **not** zero `active / active_flag / nactive / last / previous_drive`
independently because those fields jointly implement lazy integration.

The next study should use a coherent scheduler intervention at the frozen
`-20` boundary: materialize neural state first, then rebuild scheduler
bookkeeping consistently while preserving `v/g`, adaptation, current drive,
synaptic memory and the exact terminal sequence.

This tests scheduler-history carry without creating an internally inconsistent
brain state.

## Governance

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
