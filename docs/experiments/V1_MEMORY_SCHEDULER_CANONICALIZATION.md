# V1 Reward Memory Scheduler Canonicalization Audit

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Purpose

Runs #153 and #154 excluded or weakened the major independently-clearable
transient-state candidates. The remaining question is whether the apparent
history carry sits in Stonkfly's lazy-integration scheduler bookkeeping rather
than in a single physiological trace.

This study uses a coherent scheduler canonicalization instead of independently
zeroing coupled scheduler arrays.

## Fresh trajectories

- SC1 / 3503
- SC2 / 3511
- SC3 / 3517
- SC4 / 3527

The event remains the first natural reward at or after decision index 60.
No seed replacement is allowed.

## Shared protocol

Both conditions independently rebuild the same paired reward/no-pulse memory,
state-clear before recall, disable learning, freeze weights, replay exact
source lags `-60 ... -21`, apply the frozen boundary operation, then replay
the identical `-20 ... 0` terminal sequence.

## Conditions

### intact

No boundary change.

### canonical_scheduler

The pinned kernel materializes all neuron states at each observation boundary.
At the frozen boundary after lag `-21`, preserve all physiological state and
synaptic memory, then canonicalize only scheduler bookkeeping:

1. `previous_drive := drive`;
2. `last := cursor - 1` for every neuron;
3. rebuild the active set using the pinned kernel predicate:

`v > -45 OR drive > (-45-rest) OR drive+g > (-45-rest)`

4. rebuild `active`, `active_flag`, and `nactive` consistently.

The intervention must not change `v`, `g`, refractory/delay state,
luminance, adaptation, kernel credit traces, drive, rule traces, or synaptic
memory.

## Why this is safe

The intervention does not invent a new neural state. It reindexes the scheduler
from already-materialized physiological variables using the exact activity
predicate implemented by the pinned kernel.

If this is neutral, lazy bookkeeping itself does not explain the 3 tau
expression benefit.

If it materially changes terminal expression, the result localizes a scheduler
dependency that requires further audit before any biological interpretation.

## Governance

No tuning and no directional pass threshold.

All learning, causality, carrier-confirmation, and behavioral-promotion locks
remain closed.
