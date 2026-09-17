# V0.11 Proprioception — Turn Laterality Invariance

## Purpose

NeuroFly currently uses one representative FeCO-like joint proxy, not a six-leg body with left/right leg identity. Because that proxy has no modeled laterality, its proprioceptive receptor trajectory must not become a hidden channel for `TURN_LEFT` versus `TURN_RIGHT` motor execution.

This stage freezes that engineering boundary.

## Upstream

This PR is stacked on PR #80, which characterizes the existing engineering receptor proxy across a fixed motion/vibration sweep.

The unresolved SNpp39/SNpp41 biological polarity boundary from PR #79 remains unchanged.

## Audit

The executable audit enumerates every motor-execution sequence of length 1 through 5 over:

- `HOLD`
- `FORWARD`
- `TURN_LEFT`
- `TURN_RIGHT`

For each sequence, it constructs a mirrored sequence by swapping every `TURN_LEFT` with `TURN_RIGHT` while keeping `HOLD` and `FORWARD` unchanged.

Both trajectories are run from identical initial body state under two deterministic vibration profiles.

The gate requires equality at every step for:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

It also requires the private engineering joint mechanics (`joint_phase`, `joint_position`, `step_index`) to remain identical under the turn swap. The private `last_motor_execution` label is intentionally excluded from that equality check because it is checkpoint/control-plane state and must never enter the receptor payload.

The fixed audit covers:

- 1,364 motor sequences;
- 2 vibration profiles;
- 2,728 mirrored trajectory cases;
- 12,744 receptor-step comparisons.

## Interpretation

This gate does **not** require all motor executions to be proprioceptively indistinguishable. Reafferent consequences of different modeled mechanical classes are allowed.

It requires only this narrower rule:

> In a representative joint model with no left/right leg laterality, swapping left-turn and right-turn motor labels must not change the proprioceptive receptor trajectory.

Therefore the agent cannot receive a left/right turning cue that the current body model does not physically represent.

## Sensory firewall boundary

Every generated receptor payload must:

- pass the global unprivileged sensory guard;
- contain no action or motor-execution label;
- contain no joint phase, joint position, joint delta, world displacement, heading, reward, or desired action;
- preserve the existing FeCO receptor-domain contract.

## Not a biological claim

Passing this gate does not establish:

- biological left/right leg symmetry;
- six-leg biomechanics;
- SNpp39/SNpp41 identity or polarity;
- biological current calibration;
- millisecond timing;
- step-cycle phase;
- predictive inhibition;
- stimulation amplitude.

## Hard locks

This stage keeps all of the following false:

- `systematic_type_mapping_exposed`
- `current_calibration_authorized`
- `stimulation_enabled`
- `runtime_transduction_enabled`
- `runtime_gating_authorized`
- `neural_payload_promotion_authorized`

The result is an engineering anti-leakage / invariance gate only.
