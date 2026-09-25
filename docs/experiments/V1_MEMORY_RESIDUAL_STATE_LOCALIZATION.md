# V1 Reward Memory Residual-State Localization

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

Boundary-state run `36108551430` narrowed the candidate carrier space:

- clearing centered-rule `rate_kc/rate_dan` was exactly neutral;
- clearing NeuroFly wrapper visual history was exactly neutral;
- clearing only `v/g` changed expression strongly, but **increased** it rather
  than abolishing it.

Therefore the positive state carrying the extra-runtime benefit remains
unresolved.

This study tests the remaining state classes that can be cleared cleanly
without creating an internally inconsistent lazy-integration scheduler.

## Fresh trajectories

Frozen before execution:

- RL1 / 3407
- RL2 / 3413
- RL3 / 3419
- RL4 / 3433

The event remains the first natural reward at or after decision index 60.
Maximum acquisition is 300 decisions. No seed replacement is allowed.

## Shared protocol

Every condition uses:

1. the same trajectory;
2. the same pre-event checkpoint;
3. independently rebuilt paired reward/no-pulse synaptic memory;
4. the same five reinforcement-free post-event delay decisions;
5. initial `brain.reset(keep_memory=True)`;
6. wrapper visual-history clear;
7. learning disabled and weights frozen;
8. the exact source prefix `-60 ... -21`;
9. one frozen boundary intervention;
10. the exact identical terminal `-20 ... 0`.

Changed reward edges are defined before recall from the paired synaptic
difference.

## Conditions

### intact

No boundary modification.

### clear_refractory_delay

Reset only:

- `refractory`
- `queue`
- `queue_count`

This removes pending synaptic-delay events and refractory countdown while
leaving membrane/conductance, adaptation, luminance and lazy-scheduler
bookkeeping untouched.

### clear_luminance

Reset only Stonkfly retinal low-pass state:

- `luminance`

### clear_adaptation

Reset only:

- `adaptation`

This is especially relevant because KC spikes add adaptation and the pinned
model uses a 200 ms adaptation time constant directly in voltage evolution.

### clear_kernel_credit

Reset only the kernel-level credit/modulatory traces:

- `eligibility`
- `eligibility_last`
- `modulation`
- `modulation_last`

These are distinct from the centered rule's `rate_kc/rate_dan` arrays.

## Intervention purity

Before and after each boundary intervention, the runner hashes **all**
checkpoint fields exposed by pinned Stonkfly.

The run is invalid if any non-preregistered checkpoint field changes at the
boundary, or if paired synaptic memory changes.

A target field is allowed to already equal its initial value; a null clear is
recorded rather than treated as an execution failure.

## Deferred scheduler state

The following state is deliberately **not** modified in this run:

- `active`
- `active_flag`
- `nactive`
- `last`
- `previous_drive`

Those fields jointly implement lazy state evolution and are difficult to clear
individually without creating an inconsistent scheduler. If all four safe
interventions here fail to explain the positive carry, the scheduler state
becomes the next focused target.

## Interpretation boundary

A positive carrier candidate requires that clearing the state class reduces
terminal expression relative to intact across fresh trajectories.

An increase means the state is suppressive/modulatory rather than the positive
carrier. An exact null effect excludes that state class for this frozen recall
assay.

There is no directional pass threshold and no parameter tuning.

## Governance

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
