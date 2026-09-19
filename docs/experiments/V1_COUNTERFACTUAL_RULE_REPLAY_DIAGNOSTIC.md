# V1 Counterfactual Rule Replay Diagnostic

## Purpose

DAN Trace Recentering Intervention Run 35415979900 showed that applying the
mathematically corresponding DAN-trace coordinate transform reduced the large
positive efficacy drift by about 98% across all four matched replicates.

That intervention still allowed the learning arms to alter their own network
weights, so later neural activity could diverge between conditions.

This diagnostic removes that ambiguity.

## Frozen neural trajectory

For each fresh replicate, NeuroFly runs one real MaleCNS trajectory with:

- normal sensory input;
- no external reinforcement;
- zero DAN baseline in the live brain;
- learning disabled;
- plastic weights frozen.

Every 10 ms rate bin from that one trajectory supplies the same KC rate vector
and raw DAN rate vector to three isolated copies of the pinned plasticity rule.

The replay states never write back into the live neural network.

## Counterfactual replay conditions

### zero_baseline

- DAN input: raw DAN rate;
- initial DAN trace: source checkpoint trace.

### calibrated_unrecentered

- DAN input: raw DAN rate minus the frozen calibrated baseline;
- initial DAN trace: unchanged source checkpoint trace.

This reproduces the coordinate mismatch in isolation.

### calibrated_recentered

- DAN input: raw DAN rate minus the frozen calibrated baseline;
- initial DAN trace: source checkpoint trace minus the same baseline.

This is the coordinate-consistent replay.

## Why this isolates the rule

All three replay conditions receive the exact same neural trajectory.

Therefore differences in replayed memory drift cannot be explained by:

- different actions;
- different visual frames caused by learned behavior;
- learned weights feeding back into the connectome;
- different KC/DAN spike sequences.

The remaining differences arise inside the pinned centered plasticity rule and
its initial state.

## Endpoints

For each replay:

- first-five-decision mean efficacy drift;
- final mean efficacy drift;
- mean reward-compartment plastic drive;
- mean aversive-compartment plastic drive.

The live frozen network must show zero memory change.

## Interpretation boundary

This diagnostic can quantify how much of the observed drift follows directly
from trace initialization and baseline shifting under an identical neural
trajectory. It does not automatically authorize a causal or production claim.

The following remain false:

- `learning_validated`
- `dan_trace_state_mismatch_causal`
- `trace_recentering_remediation_validated`
- `baseline_shift_rule_effect_causal`
- `kc_dan_temporal_drive_causal`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
