# V1 Reward Memory Scheduler + Distributed-State Control

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Why this is the next layer

Run 1 of residual-state localization excluded kernel credit traces, showed
luminance and refractory/delay state behave as modulators rather than clean
positive carriers, and found adaptation relevant but heterogeneous.

The unresolved alternatives are now:

1. lazy-integration scheduler bookkeeping itself; or
2. a distributed physical state carried jointly by membrane/conductance,
   adaptation and input/delay state.

This study tests both in one fresh preregistered run.

## Fresh trajectories

- SD1 / 3501
- SD2 / 3511
- SD3 / 3527
- SD4 / 3533

No seed replacement.

## Shared protocol

All conditions use the same trajectory, pre-event checkpoint, independently
rebuilt paired reward/no-pulse synaptic memory, five-step reinforcement-free
delay, initial keep-memory state clear, exact prefix `-60...-21`, frozen
learning, zero recall reinforcement and exact terminal `-20...0`.

## Conditions

### intact

No boundary intervention.

### coherent_scheduler_rebuild

This is an **equivalence control**, not a memory clear.

At the already-materialized boundary it:

- rebases the absolute cursor to zero;
- rotates the delayed-event ring buffer so future event timing is preserved;
- rebases `last`, `eligibility_last` and `modulation_last` by the same
  cursor offset;
- rebuilds `active / active_flag / nactive` from the kernel's own
  `can_fire` criterion.

It must preserve:

- `v`
- `g`
- `refractory`
- `drive`
- `previous_drive`
- `luminance`
- `adaptation`
- synaptic memory

If this condition is endpoint-identical to intact, absolute/lazy scheduler
bookkeeping is not a biological memory carrier in this assay.

### clear_vg_adaptation

Clear only:

- `v`
- `g`
- `adaptation`

This tests interaction between the suppressive v/g state and the heterogeneous
adaptation effect.

### clear_broad_physical_transient

Clear only:

- `v`
- `g`
- `adaptation`
- `luminance`
- `refractory`
- `queue`
- `queue_count`

This is a distributed-state probe. It does not attribute any effect to one
field.

## Interpretation

- Scheduler rebuild identical to intact → scheduler bookkeeping excluded.
- Scheduler rebuild changes expression → scheduler representation itself
  requires further audit before any carrier claim.
- Composite clear reducing expression more consistently than the individual
  studies → evidence that the carry is distributed across interacting physical
  state.
- Composite clear increasing expression → those states act primarily as a
  suppressive/gating ensemble in this assay.

No directional pass threshold is preregistered.

## Governance

No decoder, learning rule, reward pulse, KC threshold, MBON weight or
production-checkpoint changes.

All scientific promotion locks remain false.
