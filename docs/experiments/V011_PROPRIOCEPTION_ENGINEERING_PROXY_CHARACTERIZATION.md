# V0.11 Proprioception — Engineering Proxy Characterization

## Purpose

This stage characterizes the existing `neurofly-feco-motion-proxy-v0.1` engineering transducer after the unresolved SNpp hook polarity boundary was frozen in PR #79.

It does **not** reopen the biological identity question and does not treat the engineering proxy as measured Drosophila electrophysiology.

## Upstream science boundary

PR #79 remains authoritative for the current polarity boundary:

- best-supported working inference remains frozen pending direct type-level evidence;
- no direct functional-driver-to-systematic-type crosswalk is promoted;
- current calibration, stimulation, runtime gating and systematic-type mapping remain locked.

This characterization is therefore intentionally systematic-type agnostic.

## What is tested

A fixed CI sweep is run across:

- joint-delta engineering values from `-2.0` through `2.0`;
- vibration engineering values from `0.0` through `2.0`.

The audit verifies that the receptor-domain proxy remains:

1. zero at neutral motion/vibration;
2. mutually exclusive across the two engineering hook-direction channels;
3. symmetric in directional magnitude for equal positive/negative engineering motion;
4. consistent between directional magnitude and `club_motion`;
5. bounded to `[0, 1]`;
6. monotonic non-decreasing in motion magnitude;
7. saturated at unit magnitude when engineering motion reaches or exceeds unit scale;
8. independent between vibration magnitude and joint-motion channels;
9. independent between joint-delta and the vibration channel.

The fixed sweep is part of the contract. Weakening the sweep causes the audit to fail closed.

## What this does not mean

Passing this gate does **not** establish:

- systematic neuron identity;
- SNpp39/SNpp41 flexion-extension polarity;
- biological current amplitude;
- conductance calibration;
- millisecond latency;
- step-cycle phase;
- predictive-inhibition timing;
- six-leg biomechanics;
- runtime systematic-type routing.

The positive/negative sign used here is only the existing engineering convention that feeds `hook_extension` and `hook_flexion` channel names. It is not a promotion of a systematic-type identity.

## Runtime and neural locks

The generated report must keep all of the following false:

- `direct_crosswalk_found`
- `polarity_resolved`
- `current_calibration_authorized`
- `stimulation_enabled`
- `runtime_transduction_enabled`
- `runtime_gating_authorized`
- `systematic_type_mapping_exposed`
- `neural_payload_eligible`
- `promotion_ready`

The characterization report is CI/human-diagnostic evidence only and is not itself a neural payload.

## Files

- `data/proprioception_engineering_proxy_characterization_v01.json`
- `src/neurofly/proprioception_engineering_proxy_characterization.py`
- `tests/test_proprioception_engineering_proxy_characterization.py`

## Expected state

A passing report has:

- `status = REVIEW_REQUIRED`
- `passed = true`
- `sample_count = 55`
- every characterization gate `true`
- every biological/runtime promotion lock `false`
