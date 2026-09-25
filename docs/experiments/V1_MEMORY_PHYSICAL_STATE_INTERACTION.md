# V1 Reward Memory Physical-State Interaction

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

Scheduler + distributed-state Run 1 established two important facts:

1. coherent scheduler reindex/rebuild is endpoint-equivalent to intact recall;
2. clearing the broad physical transient ensemble strongly suppresses neural
   expression, while clearing `v/g + adaptation` alone does not.

The unresolved question is whether the broad effect comes from:

- subsystem A: `v/g + adaptation`;
- subsystem B: `luminance + refractory + delayed-event queue`; or
- an interaction between A and B.

## Fresh trajectories

Frozen before execution:

- PI1 / 3607
- PI2 / 3613
- PI3 / 3617
- PI4 / 3623

No seed replacement.

## Shared protocol

Every condition uses the same trajectory, same pre-event checkpoint,
independently rebuilt paired reward/no-pulse synaptic memory, five
reinforcement-free delay decisions, initial keep-memory state clear, exact
prefix `-60...-21`, boundary intervention after lag -21, exact terminal
`-20...0`, frozen learning and zero recall reinforcement.

## Conditions

### intact

No boundary intervention.

### coherent_scheduler_rebuild

The same equivalence-control transform validated in the previous study:

- rebase cursor/time origin;
- rotate delayed-event queue ring without changing event timing;
- rebase lazy timestamps;
- rebuild active bookkeeping from materialized physical state.

Physical transient arrays and synaptic memory must remain unchanged.

### clear_vg_adaptation — subsystem A

Clear only:

- `v`
- `g`
- `adaptation`

### clear_input_delay — subsystem B

Clear only:

- `luminance`
- `refractory`
- `queue`
- `queue_count`

### clear_broad_physical_transient — A+B

Clear both subsystem A and subsystem B fields.

## Interaction analysis

For each aggregate endpoint, report the descriptive interaction contrast:

`A+B - A - B + intact`

A negative contrast means the combined clear suppresses that endpoint more
than expected from additive subsystem effects.

This is descriptive mechanism localization. There is no preregistered
significance threshold or promotion criterion.

## Interpretation boundaries

- Scheduler rebuild remains an equivalence control, not a memory clear.
- A-only, B-only and A+B are subsystem perturbations, not single-neuron or
  single-state causal claims.
- Reward-cue action divergence caused by abrupt clears is not treated as
  stronger memory evidence.
- No result opens learning validation or behavioral promotion.

## Governance

No decoder, reward pulse, KC threshold, MBON weight, learning rule, production
checkpoint or promotion lock changes.

All scientific promotion locks remain false.
