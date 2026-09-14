# V0.10 Proprioception Session Context Routing

Status: context-only routing candidate; no proprioceptive MaleCNS current.

## Causal rule

NeuroFly uses a one-decision delay:

```text
decision N-1
  -> actually executed motor action
  -> private virtual joint dynamics
  -> FeCO receptor-domain transduction
  -> proprioception context for decision N
```

Decision N can never use proprioception created by decision N itself.

## Actual execution, not requested action

The virtual body advances from the action actually applied at the body/controller boundary. If a controller changes a requested `FORWARD` into `HOLD`, the proprioceptive body receives `HOLD`.

World displacement is deliberately irrelevant to this body update. Therefore:

- an open `FORWARD` and a wall-blocked `FORWARD` can produce the same internal joint-motion proprioception;
- tactile mechanosensation separately reports the blocked contact;
- a controller-overridden `FORWARD -> HOLD` does not become false walking proprioception.

This keeps external touch and internal body motion as distinct sensory modalities.

## Neural-visible payload

Only the previously reviewed receptor-domain payload enters session context:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

The payload keeps:

- `claw_position_available=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

Private `motor_execution`, `joint_phase`, `joint_position`, raw `joint_delta`, and raw mechanical vibration are never inserted into the neural-visible proprioception payload.

## Episode resets and stale decisions

A terminal episode resets the virtual body and next-episode proprioception to neutral. A neural decision that becomes stale because the world changed episodes while it was computing cannot advance the body.

This prevents the previous episode's final joint motion from leaking into a newly reset fly.

## Checkpoint semantics

Two different things are persisted:

1. `_virtual_body_state`: private checkpoint-only mechanics needed for deterministic continuation;
2. `_pending_proprioception`: already-transduced receptor-domain payload for the next decision.

The private state is not placed into brain context. Restored pending proprioception is revalidated by the strict receptor contract and privilege guard before use.

## Current MaleCNS boundary

This stage intentionally does **not** add a proprioception reader or current path to `MaleCNSBrain`. At this stage the payload can be recorded/inspected in the session context while the connectome runtime ignores it.

Current calibration and neuron stimulation require a later evidence gate. In particular, the active crosswalk has one clean hook type (`SNpp39`) and three clean club types (`SNpp58/59/60`), but this alone is not enough to invent extension-vs-flexion subtype tuning or current amplitudes.

## Known architectural debt outside this PR

`GoalMazeSession` still supplies world-state fields used by the existing visual adapter path, and `MaleCNSBrain` currently performs retinalization using `fly`/`enemies` context internally. This is not used as direct proprioceptive input, but it means the visual transduction boundary is not yet physically isolated outside the brain object.

A future neural-context firewall should move/encapsulate visual world-truth consumption on the sensory-transducer side before the MaleCNS decision interface. This PR does not silently change that older visual architecture.

## PASS meaning

A PASS establishes only that the stateful virtual body can feed delayed, receptor-domain proprioceptive context through the session without using world displacement and without enabling neural current.

It does not establish biological joint mechanics, leg-specific routing, six-leg gait, natural efference-copy/presynaptic-inhibition mechanisms, or behavioral benefit.
