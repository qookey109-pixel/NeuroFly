# V0.11 Proprioception — Session Checkpoint Continuity

## Purpose

This stage extends the body-level restart equivalence from PR #82 to the actual
`TemporalGoalMazeSession` sensory handoff boundary.

The question is narrow:

> If NeuroFly saves and restores a running session, does the next
> proprioceptive receptor sample seen by the neural agent remain exactly the
> same as it would have been without the restart?

The gate also verifies that the human-only temporal history remains
non-persistent and never re-enters neural context.

## Coverage

The executable audit runs:

- every action sequence of length 1 through 3 over
  `HOLD / FORWARD / TURN_LEFT / TURN_RIGHT`;
- eight explicit length-5 stress sequences;
- a checkpoint at every possible split point, including before the first action
  and after the final action.

Frozen coverage:

- 92 execution sequences;
- 360 checkpoint/restore cases;
- 556 post-restore neural proprioception handoff comparisons.

## Required continuation invariants

For every checkpoint split:

1. `_pending_proprioception` is serialized exactly.
2. `_virtual_body_state` is serialized exactly.
3. A fresh restored session reconstructs both values exactly.
4. Every subsequent `context["proprioception"]` equals uninterrupted execution
   at the same action index.
5. The private virtual-body continuation also remains identical.
6. Every restored receptor payload still passes the unprivileged sensory guard.

This is specifically a **session handoff continuity** check. It is stronger
than merely checking that `VirtualFeCOJointBody.restore(...)` round-trips.

## Human-only temporal history boundary

`ProprioceptionTemporalRecorder` is diagnostic state only.

The checkpoint must not contain:

- `proprioception_temporal`;
- temporal history;
- `last_observed_proprioception`;
- `human_diagnostics`.

Immediately after restoring a session, the temporal recorder must therefore be
empty. The first new post-restore neural handoff becomes diagnostic sequence
`1` in the new process.

This reset is intentional. It must not change the receptor payload given to the
brain.

## Restore is not a sensory event

Constructing a restored session must not itself record a proprioceptive event.
Only an actual neural handoff may advance the temporal recorder.

## Scientific boundary

Passing this gate does not establish:

- SNpp39/SNpp41 polarity;
- biological current or conductance;
- biological timing or latency;
- step-cycle phase;
- predictive inhibition;
- six-leg biomechanics;
- biological memory across restart.

It establishes only deterministic software continuation of the current
engineering receptor-domain state.

## Locks

This stage keeps all of the following false:

- `systematic_type_mapping_exposed`
- `current_calibration_authorized`
- `stimulation_enabled`
- `runtime_transduction_enabled`
- `runtime_gating_authorized`
- `neural_payload_promotion_authorized`

The unresolved polarity boundary from PR #79 remains unchanged.
