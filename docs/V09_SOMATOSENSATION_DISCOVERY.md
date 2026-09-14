# V0.9 Somatosensation Discovery

Status: annotation discovery only. No somatosensory current or normal-runtime transduction is enabled by this phase.

## Goal

Add body-touch and proprioceptive sensing without weakening NeuroFly's core rule:

> The agent receives only fly-accessible sensory transduction, never privileged world truth.

This phase asks a narrower question first: does the exact pinned prepared MaleCNS annotation table expose curator-labelled first-order tactile and proprioceptive sensory populations that can support later biological crosswalk work?

## Exact annotation membership

The read-only audit recognizes only two exact curator classes:

- `mechanosensory_tactile` → tactile/contact candidate population
- `mechanosensory_proprioceptive` → proprioceptive candidate population

Membership is case-insensitive but otherwise exact. Descriptive words such as `bristle`, `chordotonal`, `campaniform`, `hair plate`, `club`, `claw`, `hook`, or `proprio` never create membership on their own.

The broader curator class `mechanosensory` is reported only as context. It is not promoted into the V0.9 tactile/proprioceptive populations. This prevents this discovery phase from silently absorbing head mechanosensors or the already integrated JO-C/JO-E antennal pathway.

## Why these classes are biologically plausible

Virtual Fly Brain MaleCNS records expose exact examples of:

- `mechanosensory_tactile` / `mechanosensory bristle` sensory neurons such as SNta04/SNta07/SNta11/SNta18.
- `mechanosensory_proprioceptive` / `chordotonal organ` sensory neurons such as SNpp39/SNpp40/SNpp50/SNpp51/SNpp58/SNpp59/SNpp60.

Examples of the latter are curated as femoral chordotonal organ club, claw, or hook neurons. This is consistent with the established Drosophila proprioceptive literature in which femoral chordotonal afferents separate into functionally distinct club, claw, and hook projections.

Recent wing-proprioception work also identifies campaniform sensilla, chordotonal organs, and hair plates as proprioceptive receptor classes, while mechanosensory bristles provide external tactile sensing.

Reference context:

- Virtual Fly Brain MaleCNS records for SNta and SNpp sensory neurons.
- Systematic annotation of the adult male Drosophila nerve cord connectome (MANC/MaleCNS sensory annotation work).
- Peripheral anatomy and central connectivity of proprioceptive sensory neurons in the Drosophila wing, eLife (2026).
- Divergent neural circuits for proprioceptive and exteroceptive sensing of the Drosophila leg, Nature Communications (2025).

## What a PASS means

A PASS establishes only that both exact curator classes are present among the retained neurons of the pinned MaleCNS/Stonkfly graph and records their annotation distributions.

It does **not** yet establish:

- which tactile neurons should represent wall, floor, enemy, food, or body contact;
- which proprioceptive neurons should encode joint angle, joint velocity, strain, stance, or self-motion;
- a body-region crosswalk;
- receptor transfer functions;
- engineering stimulation currents;
- natural firing rates;
- behavioral benefit;
- learned body control.

## No privileged contact truth

Later runtime transduction must not expose collision geometry or engine truth such as:

- wall coordinates;
- contact normal vectors with metric precision;
- object IDs or semantic labels as neural input;
- target locations;
- route/path fields;
- desired action;
- reward value.

A later tactile transducer may expose only bounded fly-relative contact channels derived from physical contact. A later proprioceptive transducer may expose only bounded body-state signals that a fly receptor could plausibly sense.

Human-only diagnostics may retain exact engine geometry for debugging, but those diagnostics must remain outside `agent_input`.

## Existing sensory stack boundary

This phase does not modify:

- compound-eye vision;
- olfaction;
- calibrated default-on JO-C/JO-E ambient-airflow mechanosensation;
- contact-only gustation;
- reward or aversive reinforcement;
- decoder policy;
- learning/plasticity policy.

`stimulation_enabled = false` and `runtime_transduction_enabled = false` are hard gates for this discovery phase.

## Next gates

If the prepared audit passes:

1. freeze exact tactile/proprioceptive annotation counts and subtype distributions;
2. identify the smallest defensible body-region / receptor-function crosswalk;
3. keep unresolved neurons unused;
4. build contact and proprioceptive transducers separately;
5. calibrate engineering currents in frozen-weight prepared MaleCNS conditions;
6. only then consider normal-runtime one-shot contact and continuous proprioceptive routing.
