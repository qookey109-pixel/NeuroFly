# V0.11 Proprioception Temporal Event Analysis

Status: **REVIEW_REQUIRED / human-only descriptive analysis**

This stage converts the already-reviewed bounded receptor history into descriptive event summaries. It does not estimate biological milliseconds, step-cycle phase, inhibitory lead time, neural current, or MaleCNS systematic-type identity.

## Input authority

The only accepted input is the exact history contract from `ProprioceptionTemporalRecorder`:

- schema `neurofly-proprioception-temporal-observability-v0.1`;
- source `verified-neural-handoff-receptor-domain`;
- capacity at most 36;
- exact four engineering receptor channels;
- all persistence/current/stimulation/runtime/systematic-type/neural-payload locks closed.

The analyzer rejects unknown history or sample fields. This is deliberate: adding a motor command, reward, body coordinate, world state, systematic type, or other unreviewed field must fail closed rather than silently becoming a temporal feature.

## Timebase

The only timebase is:

`decision-index-only`

One sequence increment means one successive verified neural handoff in the retained diagnostic history. It does **not** mean a fixed biological latency and cannot be converted into milliseconds from this contract.

The output therefore fixes:

- `milliseconds_inferred=false`
- `step_cycle_phase_resolved=false`
- `inhibitory_lead_time_resolved=false`

This matches the predictive-inhibition evidence gate in PR #70: hook-class presynaptic inhibition is biologically supported, while existing calcium data do not provide sufficient temporal resolution to parameterize a phase-resolved or millisecond gating kernel.

## Event definition

For each engineering receptor channel independently, a sample is descriptively active when its already-validated receptor level is greater than zero.

A contiguous run of active retained samples forms one **observed event**. Each event may contain only:

- `observed_start_sequence`
- `observed_end_sequence`
- `observed_duration_decisions`
- `peak_level`
- `left_censored`
- `right_censored`

The analyzer also reports active-sample count and rising/falling transitions that are actually visible inside the retained window.

## Censoring rule

The bounded history cannot prove what happened immediately before its first retained sample or immediately after its last retained sample.

Therefore:

- if the first retained sample is already active, that event is `left_censored=true`;
- if the final retained sample remains active, that event is `right_censored=true`;
- an active first sample is never counted as a rising transition merely because the buffer begins there;
- an active final sample is never counted as a falling transition.

When a 36-sample buffer has discarded older samples, `window_left_censoring_possible=true` additionally records that the retained sequence begins after sequence 1.

These rules prevent the diagnostic layer from inventing a true onset or offset that was not observed.

## Runtime placement

`TemporalGoalMazeSession` derives the event analysis only from its human-only `ProprioceptionTemporalRecorder.snapshot()` and stores the result under:

`human_diagnostics.proprioception_temporal_analysis`

The analyzer does not receive neural decisions, actions, reward, world state, private body state, or systematic neuron identities. It cannot influence the brain handoff.

The production public-state allowlist is intentionally unchanged in this stage: the already-reviewed raw temporal history remains the publication surface. The derived analysis can be independently reproduced from that history and does not need another public payload field yet.

## Hard locks

The analysis output fixes all of the following:

- `motor_command_used=false`
- `reward_used=false`
- `world_state_used=false`
- `private_body_state_used=false`
- `systematic_type_mapping_exposed=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_gating_authorized=false`
- `neural_payload_eligible=false`
- `analysis_persistence_enabled=false`

No event or transition may be interpreted as evidence that SNpp39 is extension-sensitive or that SNpp41 is flexion-sensitive. Those remain `PHYSIOLOGY_SUPPORTED_INFERENCE` until a direct type-level crosswalk is independently established.

## Next research use

This descriptive layer is sufficient for questions such as:

- whether the engineering hook proxy produces isolated versus multi-decision pulses;
- whether extension/flexion proxy events alternate cleanly;
- how often event boundaries are censored by the 36-sample window;
- whether a future phase-resolved biological dataset can be compared against the engineering event topology without changing the receptor history contract.

It is **not** sufficient to implement predictive inhibition. That remains gated by PR #70's requirement for quantitatively time-resolved physiology and independently validated MaleCNS target routing.
