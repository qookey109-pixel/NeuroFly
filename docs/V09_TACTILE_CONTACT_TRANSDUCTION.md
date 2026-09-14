# V0.9 Contact-Only Tactile Transduction

Status: engineering sensory contract only. MaleCNS tactile current injection remains disabled.

## Purpose

PR #38 established a conservative prepared-MaleCNS leg-touch candidate population of 590 neurons across six exact SNta types. This stage does **not** stimulate that population. It only defines the first runtime physical-contact fact that may later be calibrated into that population.

## Supported contact fact

The current maze body proxy emits a tactile event only when all of the following are true:

1. the action actually applied by the environment is `FORWARD`;
2. the fly position before and after the action is identical;
3. the step is non-terminal.

This is treated as a bounded **front external-touch proxy** for the current grid physics.

`TURN_LEFT`, `TURN_RIGHT`, and `HOLD` never become touch merely because the fly does not translate. A successful `FORWARD` is not touch. Predator/body terminal collisions are outside this v1 contract and are not inferred from reward or event labels.

## Agent payload

The only neural-eligible payload is:

```json
{
  "model": "neurofly-contact-mechanosensation-v1",
  "available": true,
  "encoding": "blocked-forward-external-touch-proxy",
  "contact": true,
  "channels": {"front": 1.0},
  "stimulation_enabled": false
}
```

No object ID, wall coordinate, map location, collision normal, route, reward, target class, or desired action is present.

## One-shot latch

A blocked-forward event sets one boolean session latch:

`pending_tactile_contact = true`

At the next neural decision the latch becomes exactly one tactile pulse and is immediately cleared. A later decision receives `front=0.0` unless a new physical contact occurred.

The checkpoint persists only this boolean latch. It does not persist collision geometry or a world-state explanation for the contact.

## Applied-action rule

`CurriculumMazeEnvironment` may transparently override a raw MaleCNS action for anti-stall handling. Contact detection therefore uses the **actually applied action** (`last_applied_action`) when available, not merely the raw neural decision. This prevents a raw `HOLD` that was externally converted into a blocked `FORWARD` from being mislabeled, and prevents a raw `FORWARD` that was converted into a turn from falsely generating contact.

## Sensory contract

`neurofly-sensory-contract-v0.4` now exposes `contact_mechanosensation` as a real contact-gated modality rather than a reserved placeholder. Proprioception remains reserved and unavailable.

The contact payload must pass the same no-privileged-world-state recursive guard used by the other NeuroFly senses.

## Scientific boundary

This stage is an engineering external-touch proxy, not a reconstruction of six-leg bristle biomechanics or receptor transduction. The 590-neuron crosswalk establishes candidate anatomy only; it does not establish current amplitude, receptor gain, laterality, temporal kernel, or behavioral validity.

## Gates before current injection

Before tactile current can enter MaleCNS, all of the following are required:

- general NeuroFly CI PASS;
- contact semantics tests PASS;
- one-shot session routing PASS;
- checkpoint persistence PASS;
- no privileged geometry in neural input;
- the PR #38 590-neuron crosswalk remains unchanged and valid;
- a separate prepared-MaleCNS current calibration sweep.

Until that calibration stage passes, `stimulation_enabled=false` is a hard boundary.

## Scope exclusions

This stage does not change:

- the 590-neuron tactile crosswalk;
- JO-C / JO-E airflow mechanosensation;
- gustation;
- compound-eye vision;
- olfaction;
- proprioception;
- reward / reinforcement;
- decoder policy;
- learning / plasticity policy;
- merge state of any stacked PR.
