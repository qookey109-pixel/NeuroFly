# V1 Reward Memory Prefix Specificity Control

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

History-expression run `36104612747` showed that, after state clearing, an
exact 3 tau prereward history produced a much more continuous paired
KC→MBON07 expression state through the common terminal `-20 ... 0` window
than a fresh 1 tau replay.

That result still leaves one important alternative:

> Is the benefit specific to the temporal organization of the earlier history,
> or does almost any extra 40 decisions merely warm the network into a more
> expressive state?

This audit tests that distinction without changing model parameters.

## Fresh trajectories

Four new seeds are frozen before execution:

- PS1 / 3203
- PS2 / 3209
- PS3 / 3217
- PS4 / 3221

For each seed, the selected event is the **first natural reward at or after
decision index 60**. Maximum acquisition is 300 decisions. A seed with no
qualifying reward is invalid and is not replaced.

## Two matched 60-step conditions

Both conditions use the same fresh trajectory, the same pre-event checkpoint,
the same paired reward/no-pulse memory construction, the same five
reinforcement-free delay decisions, state clearing, frozen plasticity, and zero
recall reinforcement.

### Exact-history condition

Replay:

`-60, -59, ... -21, -20, ... -1, 0`

where lag `0` is the exact reward-event cue, delivered with no reinforcement
during recall.

### Rotated-prefix control

Take the exact 40 source frame/context pairs from original lags
`-60 ... -21` and rotate them left by exactly **20 positions**.

The source-lag order therefore becomes:

`-40 ... -21, -60 ... -41`

Then replay the exact unchanged terminal sequence:

`-20 ... -1, 0`

This control preserves:

- total recall length;
- all 40 early frame/context pairs;
- all 20 terminal prereward frame/context pairs;
- the reward-event cue;
- the paired synaptic memory state;
- the number of network updates.

It changes only the temporal placement/order of the early 40-step prefix.

## Primary comparison

The primary comparison is again restricted to the identical terminal replay
window:

`-20 ... 0`

The early prefix exists only to establish state before that window.

Changed reward edges are defined before recall from the paired
reward/no-pulse synaptic difference. Recall outcomes do not select edges.

## Descriptive endpoints

Within the common terminal window, both conditions report:

- changed-KC engagement;
- changed-edge paired L1 engagement;
- MBON07 state and spike differences;
- DNp20 / DNpe017 state differences;
- action divergence;
- reward-cue action divergence;
- per-lag paired expression metrics.

There is no directional pass threshold.

## Interpretation boundary

If the exact prefix produces more stable terminal expression than the rotated
control, that supports a narrower claim that the early temporal sequence has
specific causal value beyond generic extra runtime.

If exact and rotated conditions are similar, the prior 3 tau advantage may
instead reflect nonspecific warmup, aggregate sensory exposure, or internal
state accumulation that does not require the exact early ordering.

This exploratory study does **not** validate learned behavior or authorize
behavioral promotion.

No tuning is permitted:

- no decoder/gain changes;
- no reward-pulse changes;
- no KC-threshold changes;
- no MBON-weight changes;
- no learning-rule changes;
- no seed replacement;
- no post-hoc control redesign.

## Governance

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
