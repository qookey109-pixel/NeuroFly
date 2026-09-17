# V0.11 Proprioception — Checkpoint Continuation Equivalence

## Purpose

NeuroFly is designed for long-running sessions. A checkpoint/restart boundary must not change the future proprioceptive receptor trajectory merely because the process was restored.

This stage freezes that engineering continuity rule for the current representative FeCO joint body.

## Upstream

This PR is stacked on PR #81, which verifies that the representative joint cannot leak `TURN_LEFT` versus `TURN_RIGHT` laterality through the receptor trajectory.

The unresolved SNpp39/SNpp41 biological polarity boundary remains unchanged.

## Audit

The audit enumerates all motor-execution sequences of length 1 through 5 over:

- `HOLD`
- `FORWARD`
- `TURN_LEFT`
- `TURN_RIGHT`

For every sequence and two deterministic vibration profiles, the audit:

1. runs an uninterrupted reference trajectory;
2. creates a checkpoint at every possible split point, including before the first step and after the final step;
3. restores a fresh `VirtualFeCOJointBody` from that checkpoint;
4. verifies the restored private state exactly matches the frozen checkpoint;
5. continues the remaining suffix and compares every future receptor sample against the uninterrupted reference;
6. compares private joint phase/position/step index after every resumed step;
7. verifies every resumed receptor payload still passes the global unprivileged sensory guard.

Fixed coverage:

- 1,364 execution sequences;
- 2 vibration profiles;
- 15,472 checkpoint/restore cases;
- 36,712 post-restore receptor-step comparisons.

## Checkpoint boundary rule

`restore(...)` must not itself emit a receptor event. The first receptor sample after a restart must be the same sample that would have appeared at that point in uninterrupted execution.

The checkpoint is private body/control-plane state. It is not neural input and must not be replayed as sensory history.

## Interpretation

Passing this gate means only that the current deterministic engineering body proxy has restart-stable proprioceptive continuation under the frozen test envelope.

It does **not** establish biological memory, biological temporal continuity, six-leg biomechanics, systematic neuron identity, biological current calibration, millisecond timing, predictive inhibition, or stimulation amplitude.

## Hard locks

The stage keeps all of the following false:

- `systematic_type_mapping_exposed`
- `current_calibration_authorized`
- `stimulation_enabled`
- `runtime_transduction_enabled`
- `runtime_gating_authorized`
- `neural_payload_promotion_authorized`

This is an engineering reproducibility/continuity gate only.
