# V0.11 Proprioception Temporal Runtime Observability

Status: **REVIEW_REQUIRED / human diagnostics only**

This stacked stage integrates the bounded temporal recorder from the preceding temporal-observability contract into the actual GoalMaze training path. It does not authorize proprioceptive current, stimulation, or an executable SNpp39/SNpp41 polarity mapping.

## Stack authority

Base: `feature/v0.11-proprioception-temporal-observability` (Draft PR #68).

Inherited facts remain unchanged:

- engineering receptor model: `neurofly-feco-motion-proxy-v0.1`;
- engineering encoding: `virtual-joint-motion-only-proxy`;
- bounded history capacity: at most 36 samples;
- direct `SNpp39/SNpp41 <-> flexion/extension` type-level crosswalk remains unresolved;
- `SNpp39 ≈ extension-sensitive hook` and `SNpp41 ≈ flexion-sensitive hook` remain `PHYSIOLOGY_SUPPORTED_INFERENCE`, not runtime bindings.

## Exact observation point

Production self-training now uses `TemporalGoalMazeSession`.

The temporal sample is **not** taken from `pending_proprioception` and is not taken before the Neural Context Firewall. `TemporalGoalMazeSession._prepare_brain_handoff(...)` first delegates to the existing `GoalMazeSession._prepare_brain_handoff(...)`. Only after that method has constructed and validated the handoff bundle does the recorder copy:

`handoff_context["proprioception"]`

into the human-only bounded history.

Therefore the temporal sequence represents the exact receptor-domain proprioception payload prepared for that neural handoff. The future pending receptor pulse remains outside the current sample.

## Temporal contract

The existing `ProprioceptionTemporalRecorder` remains authoritative:

- schema: `neurofly-proprioception-temporal-observability-v0.1`;
- source: `verified-neural-handoff-receptor-domain`;
- maximum capacity: 36;
- only four receptor channels are stored:
  - `hook_extension`
  - `hook_flexion`
  - `club_motion`
  - `club_vibration`
- history is `human_only=true`;
- `history_persistence_enabled=false`;
- `neural_payload_eligible=false`;
- `systematic_type_mapping_exposed=false`;
- `current_calibration_authorized=false`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`.

No private joint phase/position, motor command, world displacement, reward, desired action, systematic-type label, or SNpp identity is stored.

## Checkpoint boundary

Temporal history is intentionally session-local human observability and is not added to `GoalMazeSession.save()`.

Existing checkpoint persistence remains limited to the already-authorized environment/session state, including private virtual-body checkpoint state and the single already-transduced pending proprioception payload required for the next decision. A restored process starts with an empty temporal diagnostic history.

## Public-state boundary

The production training publisher previously sanitized gameplay through `_public_goal_state(...)`. This stage adds an explicit human-diagnostic allowlist containing only:

- `proprioception`
- `proprioception_temporal`

These values are deep-copied. Any other future `human_diagnostics` key is not automatically published. This also closes the earlier gap where the PR #64 live receptor diagnostic could exist in the session snapshot but be omitted by the production public-state sanitizer.

## Website observability

The existing proprioception HUD retains three separated planes:

1. **LIVE RECEPTOR INPUT** — latest exact receptor handoff;
2. **RECENT RECEPTOR HISTORY** — bounded verified handoff history;
3. **CONTROL PLANE** — unresolved systematic-type semantics.

The history renderer fails closed unless all of the following hold:

- expected temporal schema and source;
- `human_only=true`;
- integer capacity between 1 and 36;
- `sample_count == samples.length <= capacity`;
- monotonically contiguous positive sequence IDs within the retained window;
- exact four receptor channel keys with finite values in `[0,1]`;
- every runtime/current/systematic-type/neural-payload lock remains closed.

The UI renders at most the most recent eight samples to keep the HUD compact; the diagnostic object itself retains up to 36.

## Regression gates

Tests require:

- sample 1 and sample 2 exactly match the corresponding neural handoff proprioception channels;
- the delayed FORWARD receptor consequence appears on the next decision, not the previous sample;
- after 40 handoffs only sequences 5..40 remain;
- temporal history never appears in neural context;
- private body/world/systematic-type fields never appear in the history;
- history is absent from the checkpoint and resets across process restore;
- the public-state sanitizer publishes only the two explicitly allowed proprioception diagnostics;
- fallback state and live relay both invoke the temporal HUD renderer;
- the website retains the no-SNpp-alias and no-proprioceptive-current warning.

## Hard locks

This stage does **not**:

- bind `hook_extension` to SNpp39 or SNpp41;
- bind `hook_flexion` to SNpp39 or SNpp41;
- inject proprioceptive current;
- calibrate proprioceptive current;
- stimulate any SNpp population;
- route control-plane semantics into the neural payload;
- persist the temporal history;
- merge the science stack automatically.

The next scientific step should use this temporal observability to evaluate receptor timing and circuit-level temporal hypotheses without treating the current SNpp39/SNpp41 polarity inference as direct type-level physiology.
