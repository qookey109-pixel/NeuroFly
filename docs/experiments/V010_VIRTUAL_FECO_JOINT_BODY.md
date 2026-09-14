# V0.10 Virtual FeCO Joint Body Proxy

Status: engineering body-layer candidate; no neural current; no normal runtime routing.

## Purpose

NeuroFly needs a body between motor execution and proprioceptive sensory input. Raw game position, heading, route progress, reward, or world displacement must not be relabeled as proprioception.

This stage therefore introduces a stateful **representative femur-tibia joint** whose private mechanics can be transduced through the already-defined FeCO motion contract.

Pipeline for this stage:

```text
executed motor mode
  -> private representative joint state
  -> joint displacement / optional internal vibration
  -> FeCO motion transducer
  -> hook / club receptor-domain channels
```

The first two lines are private body mechanics. Only the final receptor-domain payload is eligible to become neural input in a later stage.

## Biological evidence boundary

Drosophila FeCO is a leg proprioceptive organ that monitors femur-tibia joint kinematics. Published work supports the functional division used by the NeuroFly receptor contract:

- claw neurons: tibia position;
- hook neurons: directional tibia movement;
- club neurons: bidirectional tibia movement and vibration.

References:

- Mamiya et al., *Neural coding of leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC6481666/
- Agrawal et al., *Central processing of leg proprioception in Drosophila*: https://elifesciences.org/articles/60299
- Chen et al., *Functional architecture of neural circuits for leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC8665017/

Walking Drosophila show coordinated six-leg gait patterns, including modified-tripod organization. That evidence is relevant to a future multi-leg body model:

- Mendes et al./related gait analysis, *Drosophila uses a tripod gait across all walking speeds...*: https://elifesciences.org/articles/65878

**NeuroFly v0.10 does not claim to reproduce those six-leg mechanics.** The current MaleCNS crosswalk has not yet established sufficiently clean leg-specific FeCO type identity for such a model.

## Model

`neurofly-representative-feco-joint-body-v0.1`

Policy:

`stateful-motor-execution-to-private-joint-mechanics-no-world-kinematics`

Private state:

- `joint_phase`
- `joint_position`
- `step_index`
- `motor_execution`

These fields are checkpoint/diagnostic state only. The global sensory privilege guard rejects them if they are accidentally inserted into neural input.

## Engineering dynamics

This is deliberately a compact proxy, not measured fly biomechanics.

- `FORWARD` advances a representative cyclic joint through a full-amplitude excursion.
- `TURN_LEFT` and `TURN_RIGHT` advance the same representative joint through the same smaller excursion.
- `HOLD` passively returns the representative joint toward neutral.
- external/internal mechanical vibration can be supplied separately, but the motor action does not synthesize a fake vibration signal.

Left and right turns intentionally have identical representative-joint envelopes. The model has no leg laterality and therefore cannot smuggle the controller's turn direction into proprioception.

## Neural-visible output

Only the existing bounded FeCO receptor contract is returned:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

The payload continues to enforce:

- `claw_position_available=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

Claw remains REVIEW_REQUIRED because the conservative MaleCNS crosswalk rejected `SNpp50/51` as clean active types.

## Explicitly forbidden as proprioceptive input

The body proxy does not accept or export solved world-state features such as:

- world `x/y`
- heading
- world velocity
- world displacement
- route/path state
- reward
- desired action

Its internal `motor_execution`, `joint_phase`, `joint_position`, raw `joint_delta`, and raw `mechanical_vibration` are also forbidden from direct neural input. Only their receptor-domain transduction may cross the sensory boundary.

## What this PASS would mean

If unit/CI validation passes, it establishes only that NeuroFly now has a stateful, versioned body-mechanics boundary capable of producing non-privileged hook/club-like receptor channels.

It does **not** establish:

- natural Drosophila joint biomechanics;
- a six-leg model;
- modified-tripod reproduction;
- active-movement presynaptic inhibition;
- leg-specific MaleCNS routing;
- proprioceptive current amplitude;
- runtime proprioceptive stimulation;
- behavioral benefit or biological validation.

## Next gate

After this body proxy passes, the next stacked stage may route its receptor-domain payload through `GoalMazeSession` as **sensory context only**, while keeping MaleCNS proprioceptive current disabled. The session must advance the body from the action actually executed by the body/controller boundary, not from world displacement.

Only after session routing is independently tested should prepared-MaleCNS current calibration be considered.
