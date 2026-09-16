# V0.11 Proprioception Hook Temporal Topology

Status: **REVIEW_REQUIRED / human-only engineering topology analysis**

This stacked stage adds a stricter descriptive analysis over the reviewed bounded proprioception history. Its purpose is to audit the temporal structure of the engineering `hook_extension` / `hook_flexion` proxy before any biological current calibration or systematic-type routing is considered.

## Stack authority

Base: Draft PR #72, branch `feature/v0.11-proprioception-temporal-event-visualization`, exact head `7705f259f47c637423890604fea61d023e185e8c`.

Inherited boundaries remain unchanged:

- receptor model: `neurofly-feco-motion-proxy-v0.1`;
- encoding: `virtual-joint-motion-only-proxy`;
- temporal source: `verified-neural-handoff-receptor-domain`;
- maximum history capacity: 36;
- only decision-index time is available;
- direct `SNpp39/SNpp41 <-> flexion/extension` type-level crosswalk remains unresolved;
- no proprioceptive current, current calibration, stimulation, predictive-inhibition runtime gating, or systematic-type routing is authorized.

## Why topology is checked

The engineering receptor encoder derives directional hook channels from the sign of a private virtual joint displacement:

- positive delta -> `hook_extension`;
- negative delta -> `hook_flexion`;
- magnitude -> `club_motion`.

The two hook channels are therefore required to be mutually exclusive. `club_motion` must also cover the active directional hook magnitude.

This stage re-checks those invariants on the retained reviewed handoff history before computing any directional temporal topology. A violation fails closed instead of being repaired or biologically interpreted.

## Input firewall

The analyzer reuses the exact temporal-history validator from PR #71. The accepted history remains limited to the reviewed schema and exact sample fields.

Unexpected fields such as action, motor command, reward, world state, private body state, systematic type, or SNpp identity are rejected before topology analysis.

## Directional event definition

Each retained sample is classified only from the two engineering hook receptor levels:

- `hook_extension > 0` -> extension engineering state;
- `hook_flexion > 0` -> flexion engineering state;
- both zero -> idle engineering state;
- both positive -> invalid engineering history, fail closed.

A contiguous run of the same non-idle engineering direction is one observed directional event.

Each event contains only:

- engineering direction name;
- observed start sequence;
- observed end sequence;
- observed duration in decision indices;
- peak receptor level;
- left/right censoring flags.

## Event-transition topology

For every adjacent pair of directional events, the analyzer reports:

- previous and next engineering direction;
- previous observed end sequence;
- next observed start sequence;
- idle gap measured only in decision indices;
- whether the two event directions alternate;
- whether the alternation is a direct reversal with zero retained idle samples;
- whether the reversal occurs after one or more retained idle samples;
- whether the same engineering direction re-enters after an idle gap.

Aggregate counts are descriptive only:

- directional active sample count;
- idle sample count;
- directional event count;
- event-transition count;
- alternating transition count;
- direct reversal count;
- reversal-after-idle count;
- same-direction re-entry count;
- total and maximum observed idle-gap decisions.

## Timebase boundary

The only timebase remains:

`decision-index-only`

The analysis explicitly fixes:

- `milliseconds_inferred=false`;
- `step_cycle_phase_resolved=false`;
- `inhibitory_lead_time_resolved=false`;
- `biological_identity_resolved=false`.

An observed gap of `2 decisions` means only two retained verified neural handoffs between engineering events. It is not a biological latency and cannot be converted into a 9A timing kernel.

## Censoring

The 36-sample retained window cannot establish the true state immediately outside its boundaries.

Therefore:

- an event active at the first retained sample is `left_censored=true`;
- an event active at the final retained sample is `right_censored=true`;
- if the first retained sequence is greater than 1, `window_left_censoring_possible=true`.

No true onset, offset, phase, or lead time is invented outside the observed window.

## Scientific interpretation boundary

This analysis is an engineering quality and temporal-shape diagnostic. It does **not** establish:

- that `hook_extension` is SNpp39 or SNpp41;
- that `hook_flexion` is SNpp39 or SNpp41;
- exact biological directional tuning of either systematic type;
- inhibitory current amplitude;
- biological phase;
- millisecond latency;
- 9A lead time.

The current candidates remain only:

- `SNpp39 ≈ extension-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`;
- `SNpp41 ≈ flexion-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`.

Temporal topology is not identity evidence.

## Hard locks

The analyzer output keeps all of the following closed:

- `motor_command_used=false`;
- `reward_used=false`;
- `world_state_used=false`;
- `private_body_state_used=false`;
- `systematic_type_mapping_exposed=false`;
- `current_calibration_authorized=false`;
- `stimulation_enabled=false`;
- `runtime_gating_authorized=false`;
- `neural_payload_eligible=false`;
- `analysis_persistence_enabled=false`.

## Intended next use

If this engineering topology layer remains stable under reviewed histories, it can support later human-only comparisons against genuinely time-resolved biological recordings. Such a later comparison must remain separate from systematic-type identity promotion and current calibration unless direct type-level physiology is independently established.

Do not merge automatically.
