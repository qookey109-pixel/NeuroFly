# V0.9 Tactile Current Calibration

Status: prepared-MaleCNS frozen-weight calibration only. Runtime tactile stimulation remains disabled.

## Prerequisites

This stage depends on two earlier boundaries:

1. the evidence-backed tactile leg crosswalk selects exactly 590 MaleCNS neurons across six exact types;
2. the contact-only runtime transducer emits a one-shot front-contact fact without map geometry or collision metadata.

Calibration does not change either boundary.

## Exact candidate population

The active crosswalk is `data/tactile_leg_functional_crosswalk_v02.json`.

Expected exact counts:

- `SNta20`: 156
- `SNta26`: 31
- `SNta27`: 47
- `SNta28`: 74
- `SNta34`: 54
- `SNta37`: 228

Total: **590 neurons**.

Every calibration run fails closed if an approved type has a same-name row outside `class=mechanosensory_tactile`, appears in a disallowed subclass, disappears, or changes expected count.

## Matched frozen-state design

Each current candidate is evaluated with two conditions from the same baseline checkpoint:

- `contact_off`: no tactile current;
- `front_contact`: uniform engineered current applied only to the exact 590-neuron selected population.

Learning is disabled and `weights_frozen=true`. The baseline memory SHA must match across both conditions and plastic weights must remain unchanged after simulation.

The visual scene, seed, neural duration, and prepared MaleCNS graph remain matched.

## Predeclared sweep

The workflow tests these currents:

`2, 4, 6, 8, 10, 12, 16`

The selected value is the **lowest predeclared current** that satisfies all gates.

## Response gates

A current passes only when:

- the full 590-neuron selected population has a positive spike-per-neuron delta over matched `contact_off` and contains active neurons;
- each of the six exact SNta type groups independently has a positive spike-per-neuron delta and at least one active neuron;
- exact population counts still match the audited crosswalk;
- the baseline checkpoint SHA is consistent;
- the crosswalk SHA is consistent;
- selected body IDs are consistent across the sweep;
- plasticity remains frozen.

The gate deliberately does **not** require a particular decoded movement action. Calibration is validating sensory current routing, not claiming that a tactile pulse already produces biologically correct avoidance behavior.

## Runtime boundary

Even if a current passes, this stage reports:

`runtime_stimulation_enabled=false`

The result may later be used by a separate runtime-routing PR, but calibration itself does not inject tactile current during normal NeuroFly play.

## Scientific interpretation

A PASS establishes only that an engineered current can reproducibly increase activity in the selected evidence-backed MaleCNS tactile candidates under matched frozen conditions.

It does not establish:

- natural bristle mechanics;
- force-to-current transfer functions;
- six-leg biomechanics;
- receptor adaptation;
- tactile laterality;
- contact localization;
- natural temporal kernels;
- behavioral benefit;
- biological validation.

The first runtime tactile channel remains an engineering external-touch proxy.
