# V0.11 Proprioception Temporal Observability

Status: **REVIEW_REQUIRED**

This stage adds a bounded human-only history contract for FeCO-like receptor payloads while preserving the unresolved SNpp39/SNpp41 polarity boundary.

## Goal

Keep a short temporal trace of the exact receptor-domain payloads that are eligible to be observed after a neural handoff, without converting diagnostic history into neural input, current injection, systematic-type routing, checkpoint state, reward context, or world-state telemetry.

The current bound is **36 samples maximum**.

## Temporal recorder contract

`src/neurofly/proprioception_temporal_observability.py` provides a fail-closed recorder that accepts only the existing strict engineering receptor contract:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

Every accepted sample must retain:

- model `neurofly-feco-motion-proxy-v0.1`;
- encoding `virtual-joint-motion-only-proxy`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`;
- `engineering_proxy=true`.

Unexpected fields fail closed. A diagnostic sample that attempts to carry a systematic-type mapping is rejected rather than stripped.

## Human-only boundary

The temporal snapshot explicitly declares:

- `human_only=true`;
- `history_persistence_enabled=false`;
- `systematic_type_mapping_exposed=false`;
- `current_calibration_authorized=false`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`;
- `neural_payload_eligible=false`.

The recorder does not store private joint state, motor commands, world displacement, reward, desired action, SNpp39/SNpp41 labels, or candidate polarity labels.

This first temporal-contract stage is deliberately separate from runtime-session integration. A later stacked integration must call `observe_neural_handoff(...)` only at the exact point where the already-validated receptor payload is used for a neural handoff. It must not record `pending_proprioception`, because that payload belongs to the next decision.

## New wiring-evidence review

The evidence ledger in `data/proprioception_temporal_wiring_evidence_v01.json` refreshes the current circuit boundary with the 2025 FeCO connectome study and MaleCNS systematic annotation.

The reviewed evidence supports the following descriptive circuit facts:

1. FeCO claw and hook neurons connect to local VNC interneurons and leg motor neurons, consistent with rapid proprioceptive feedback.
2. Hook flexion and hook extension populations show strongly different postsynaptic connectivity.
3. Hook axons receive substantial inhibitory presynaptic input, prominently from 9A neurons, supporting context-dependent gating of proprioceptive feedback.
4. Flexion-tuned hook/claw populations provide feedback biased toward tibia extension and against tibia flexion; extension-tuned populations show the complementary pattern.
5. MaleCNS systematic annotation places SNpp39 and SNpp41 in FeCO hook-related proprioceptive circuitry and groups both with strong 09A-related connectivity.

Primary sources:

- Lee et al., *Divergent neural circuits for proprioceptive and exteroceptive sensing of the Drosophila leg*, Nature Communications (2025): https://www.nature.com/articles/s41467-025-59302-3
- Marin et al., *Systematic annotation of a complete adult male Drosophila nerve cord connectome reveals principles of functional organisation*: https://elifesciences.org/reviewed-preprints/97766

## What this does **not** prove

None of the refreshed circuit evidence directly supplies an author-provided systematic-type tuning crosswalk.

Therefore the existing conservative interpretation remains unchanged:

- `SNpp39 ≈ extension-sensitive hook` = **PHYSIOLOGY_SUPPORTED_INFERENCE** only;
- `SNpp41 ≈ flexion-sensitive hook` = **PHYSIOLOGY_SUPPORTED_INFERENCE** only;
- `direct_snpp39_snpp41_direction_crosswalk_found=false`;
- no executable `hook_extension/flexion -> SNpp39/SNpp41` alias;
- no proprioceptive current;
- no current calibration;
- no stimulation;
- no runtime systematic-type routing.

Temporal similarity, phase relationships, anti-correlation, or consistency with a motor reflex cannot upgrade an inferred identity into direct evidence.

## Regression expectations

Tests require that:

- history capacity can never exceed 36;
- only exact strict receptor payloads are accepted;
- invalid samples do not advance the sequence;
- returned samples and snapshots are copy-safe;
- systematic-type mappings and runtime/stimulation unlocks fail closed;
- temporal history is human-only, nonpersistent, and neural-ineligible;
- private body/world/control fields and SNpp39/SNpp41 names never appear in the temporal payload.

## Next integration gate

The next stacked PR may integrate this recorder into `GoalMazeSession`, but only at the existing validated neural-handoff boundary introduced by live receptor observability. The required causal rule is:

`actual receptor payload used by decision N -> append temporal diagnostic sample N`

not:

`pending receptor consequence of decision N -> display as sample N`.

No merge is authorized by this evidence note.
