# V0.11 Proprioception Temporal Gating Evidence

Status: **REVIEW_REQUIRED / evidence only / non-executable**

This stage follows the bounded temporal handoff observability work and asks a narrower biological question:

> What temporal modulation of FeCO hook feedback is directly supported strongly enough to guide future modelling, without inventing a millisecond current kernel or resolving the still-missing SNpp39/SNpp41 direction crosswalk?

## Directly supported hook-class facts

The 2025 Nature study `Selective presynaptic inhibition of leg proprioception in behaving Drosophila` provides direct behavioural physiology and connectomic evidence that:

- FeCO hook proprioceptors are movement-encoding, phasic, and directionally tuned at the hook-class level;
- movement-encoding proprioceptor axons are selectively suppressed during self-generated walking and grooming;
- GABAergic 9A interneurons provide presynaptic inhibition to movement-encoding hook axons;
- those inhibitory neurons receive descending pathways positioned to drive context-specific and leg-specific modulation;
- inhibitory-neuron and descending-neuron activity correlates with self-generated but not passive leg movement.

The 2025 Nature Communications FeCO connectome independently supports the local circuit architecture: hook axons receive substantial inhibitory presynaptic input, prominently from 9A neurons, while hook/claw proprioceptive pathways feed local leg motor circuits.

MaleCNS systematic annotation independently places SNpp39 and SNpp41 among FeCO hook proprioceptive types in a connectivity grouping with strong 09A input.

## What this does not resolve

These results apply at the **hook-class / circuit-motif level**. They do not provide direct type-level directional physiology for SNpp39 versus SNpp41.

The existing candidates remain:

- SNpp39 ≈ extension-sensitive hook — `PHYSIOLOGY_SUPPORTED_INFERENCE`;
- SNpp41 ≈ flexion-sensitive hook — `PHYSIOLOGY_SUPPORTED_INFERENCE`.

No executable `hook_extension` / `hook_flexion` to SNpp39 / SNpp41 alias is authorized by this stage.

## Temporal-resolution boundary

The final Nature work explicitly retains an important limitation inherited from the earlier study: calcium dynamics are too slow relative to fly leg kinematics to determine the exact phase relationship of the inhibitory signal or a quantitative lead time relative to movement.

Therefore this project must not infer any of the following from those calcium traces:

- a millisecond 9A delay;
- a step-cycle phase kernel;
- an inhibitory conductance amplitude;
- a synaptic current waveform;
- direction-specific SNpp39 or SNpp41 gating.

A biologically meaningful executable temporal kernel would require faster, phase-resolved physiology (for example voltage-resolved measurements) or another independently validated quantitative source.

## What temporal observability may safely do now

The bounded receptor history can support human-only descriptive analyses such as:

- receptor pulse onset / offset;
- hook-direction pulse transitions;
- duration expressed in decision-index units;
- engineering lag between consecutive verified handoffs;
- comparison of the existing self-generated proxy histories across actions.

These summaries remain diagnostics. They cannot enter the neural payload and cannot become identity evidence.

## Motor/efference-copy boundary

The biological 9A circuit is recruited by descending and premotor pathways associated with active movement. NeuroFly must not recreate this by leaking simulator `desired_action`, motor command, position, displacement, or other privileged world/body truth into the sensory receptor history.

If a future predictive-inhibition mechanism is implemented, its control signal must come from an independently justified neural/control pathway rather than a shortcut around the sensory firewall.

## Promotion gate

Do not propose executable predictive inhibition until both conditions are met:

1. a quantitatively time-resolved source supports phase / lead-time dynamics strongly enough to parameterize a temporal kernel; and
2. the target pathway in MaleCNS has an independently validated identity/routing path that does not rely on the unresolved SNpp39/SNpp41 direction inference.

Until then:

- `runtime_gating_authorized=false`
- `phase_kernel_authorized=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `systematic_type_mapping_exposed=false`
- `neural_payload_eligible=false`

Machine-readable evidence: `data/proprioception_temporal_gating_evidence_v01.json`.
