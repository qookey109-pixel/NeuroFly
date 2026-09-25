# V1 Reward Memory Boundary-State Localization

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

Run `36105949179` showed that rotating the early `-60 ... -21` prefix did
not abolish terminal memory expression. Exact history retained modest average
advantages, but rotated history still produced changed-KC, MBON07 and action
expression in all four fresh replicates.

That means the important next question is not whether the exact early order is
strictly required. It is:

> Which transient state accumulated during the extra 40 decisions carries the
> benefit into the identical final `-20 ... 0` sequence?

## Fresh trajectories

Four new seeds are frozen before execution:

- BL1 / 3301
- BL2 / 3307
- BL3 / 3313
- BL4 / 3319

The selected event is the first natural reward at or after decision index 60.
Maximum acquisition is 300 decisions. A seed with no qualifying reward is
invalid and is not replaced.

## Shared memory construction

For every condition and replicate:

1. reconstruct the same pre-event checkpoint;
2. build paired no-pulse and reward-memory branches;
3. replay the same five reinforcement-free post-event delay decisions;
4. define changed reward edges before recall from the paired synaptic
   difference;
5. clear transient state with `brain.reset(keep_memory=True)`;
6. clear the wrapper visual-history cache;
7. disable learning and freeze weights;
8. replay exact source lags `-60 ... -21`.

The paired synaptic memory must be identical across all conditions.

## Boundary

The intervention point is frozen:

**after source lag `-21`, immediately before source lag `-20`.**

After the boundary intervention every condition receives exactly the same
terminal sequence:

`-20 ... -1, 0`

Lag `0` is the original reward-event cue, delivered with no reinforcement.

## Conditions

### 1. intact

No boundary modification.

### 2. clear_rule_traces

Clear only Stonkfly centered-rule trace arrays:

- `brain.rate_kc`
- `brain.rate_dan`

They are restored to their constructor initial arrays.

No membrane, conductance, queue, luminance, adaptation, wrapper visual state,
or synaptic memory is modified.

### 3. clear_membrane_conductance

Clear only:

- `brain.v`
- `brain.g`

They are restored to their constructor initial arrays.

All other transient fields, including rule traces, refractory state, queues,
luminance, adaptation and wrapper visual history, remain untouched.

### 4. clear_wrapper_visual_history

Clear only:

- NeuroFly wrapper `_last_visual_rgb`

No Stonkfly brain array is modified.

## Why these three first

Pinned Stonkfly `reset()` clears many state classes simultaneously:
membrane, conductance, refractory and queue state, retinal luminance,
adaptation, rule traces and other internal arrays.

Using a full reset at the boundary would therefore not localize a carrier.

This first localization layer isolates three candidate classes one at a time.
Combinations or broader neural-state resets are deferred until the single-state
controls are observed.

## Primary comparison

All primary endpoints use only the common terminal replay window:

`-20 ... 0`

For every condition, report:

- changed-KC engagement;
- changed-edge paired L1 engagement;
- MBON07 state and spike differences;
- DNp20 / DNpe017 state differences;
- action divergence;
- reward-cue action divergence;
- per-lag terminal expression metrics.

There is no directional pass threshold.

## Interpretation boundary

A state class becomes a stronger carrier candidate only if clearing that class
at the frozen boundary selectively reduces terminal expression relative to the
intact condition across fresh trajectories.

A null effect is also informative.

In particular, `rate_kc/rate_dan` participate in the centered plasticity
rule, while recall plasticity is frozen here. Clearing them may therefore have
little direct effect on neural expression; this study measures that rather
than assuming otherwise.

The study does not authorize claims of validated learning, temporal indexing,
causal memory expression, or behavioral promotion.

## Governance

No changes to:

- decoder mapping or gain;
- reward pulse;
- KC threshold;
- MBON weights;
- learning rule;
- production checkpoint.

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
