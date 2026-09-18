# V0.11 Proprioception — Self-Training Restart Orchestration Contract

## Purpose

This stage moves one level above PR #83 and exercises the production
self-training **orchestration surfaces** used around a
`TemporalGoalMazeSession`:

- the production neural-verification predicate;
- the production public-state projection;
- checkpoint/save and reconstructed session continuation;
- human-only temporal diagnostics.

The goal is to show that a process/batch boundary does not create a false
proprioceptive discontinuity in the orchestration layer.

## Important evidence limit

CI does **not** run a real MaleCNS process restart here.

The production `run_self_training()` entry point requires the real MaleCNS
preflight, data and brain checkpoint. The audit therefore uses an explicitly
synthetic CI brain fixture that satisfies the production verification predicate
while exercising the real session and public-projection code paths.

Accordingly, a passing result means:

> the production self-training orchestration contract is restart-stable for the
> proprioception path under the frozen deterministic fixture.

It does **not** mean:

> the MaleCNS brain checkpoint itself has been independently proven equivalent
> across a real process restart.

That stronger proof requires an authorized real MaleCNS execution receipt.

## Coverage

The gate covers:

- all action sequences of length 1..3;
- eight explicit length-5 stress sequences;
- every restart split point.

Frozen totals:

- 92 sequences;
- 360 restart cases;
- 556 post-restart step comparisons.

## Production surfaces exercised

Every synthetic state must pass the same
`_neural_decision_verified(...)` predicate used by self-training.

Every raw session state is transformed with the same
`_public_goal_state(...)` function used by self-training playback/live
publication.

For each post-restart step, the audit requires:

1. neural `context["proprioception"]` equals uninterrupted execution;
2. public current proprioception diagnostics equal uninterrupted execution;
3. stable public gameplay state equals uninterrupted execution after excluding
   only wall-clock/process-local surfaces;
4. private checkpoint/body fields never appear in public state;
5. human diagnostics never enter neural context;
6. restored receptor payloads still pass the unprivileged sensory guard.

## Temporal history semantics

Temporal history intentionally does **not** survive process restart.

After reconstruction:

- the temporal recorder starts empty;
- the first real neural handoff becomes sequence 1;
- subsequent sequence numbers are local to the new process;
- the latest human-only temporal sample must match the current receptor
  handoff.

The public current proprioception state must remain continuous even though the
human-only history resets.

This distinction prevents the UI from implying a continuous persisted sensory
history when no such history was checkpointed.

## Scientific and runtime boundary

This stage does not resolve or promote:

- SNpp39/SNpp41 polarity;
- systematic type mapping;
- biological current/conductance;
- biological latency;
- step-cycle phase;
- predictive inhibition;
- stimulation;
- biological memory over restart.

All existing science/runtime locks remain false.

## Next stronger proof

A future real execution receipt may separately test:

`real MaleCNS checkpoint -> process exit -> new process -> restored brain +
session -> verified neural decisions`

That proof must preserve the same sensory-only and temporal-history boundaries
and must not be inferred from this synthetic orchestration gate.
