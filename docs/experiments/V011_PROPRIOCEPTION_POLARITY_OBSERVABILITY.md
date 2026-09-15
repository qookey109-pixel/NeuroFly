# V0.11 Proprioception — polarity-agnostic website observability

Status: **HUMAN-ONLY OBSERVABILITY / REVIEW_REQUIRED**

This stage is stacked on the polarity semantic firewall. It does not change the virtual body, neural handoff, MaleCNS stimulation, current calibration, decoder, reward, or learning behavior.

## Goal

Make the current SNpp39/SNpp41 evidence boundary visible on the NeuroFly website without turning control-plane evidence into a sensory signal.

The website now exposes the exact semantic contract already enforced by the previous stage:

- `hook_direction_channel_A -> SNpp39`
- `hook_direction_channel_B -> SNpp41`
- candidate functions remain physiology-supported inference only;
- exact systematic-type polarity remains unresolved;
- `hook_extension` and `hook_flexion` remain engineering receptor-channel names with no systematic-type binding.

## Data source

`site/proprioception-semantics.json` is a human-facing snapshot of the machine semantic contract produced from `data/proprioception_hook_direction_evidence_v01.json`.

A regression test requires exact JSON equality between the website snapshot and `build_systematic_type_semantic_contract(...)`. If evidence semantics or locks change without regenerating the site snapshot, CI fails.

## Website panel

The existing HUD adds a **PROPRIOCEPTION / CONTROL PLANE** section at runtime. It shows:

- evidence status and unresolved direct crosswalk;
- Channel A / SNpp39 candidate semantics;
- Channel B / SNpp41 candidate semantics;
- engineering-channel binding status;
- runtime-routing lock;
- current-calibration lock;
- neural-payload eligibility.

Candidate function labels are explicitly marked as inference.

## Boundary

This panel is presentation-only. The semantic JSON is fetched by browser-side HUD code and is not passed to `GoalMazeSession`, `Neural Context Firewall`, `MaleCNSBrain`, or any stimulation/current path.

The semantic contract still requires:

- `plane = control-plane-only-not-neural-input`
- `systematic_type_polarity_resolved = false`
- `neural_payload_eligible = false`
- `current_calibration_authorized = false`
- `stimulation_enabled = false`
- `runtime_transduction_enabled = false`
- `promotion_ready = false`

The engineering `hook_extension` / `hook_flexion` channels must keep `systematic_type_binding = null`.

## Fail-closed website behavior

If the semantic snapshot is missing, malformed, claims resolved polarity, or becomes neural-payload eligible, the panel renders a fail-closed state rather than presenting a runtime-ready mapping.

## Scope

- website/control-plane observability only;
- no realtime proprioceptive current telemetry yet;
- no systematic-type runtime routing;
- no new biological claim;
- no automatic merge.
