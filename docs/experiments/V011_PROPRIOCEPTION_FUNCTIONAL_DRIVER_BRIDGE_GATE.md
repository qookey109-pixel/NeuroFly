# V0.11 Proprioception Functional-Driver Identity Bridge Gate

Status: **REVIEW_REQUIRED / ACCESS_REQUIRED**.

This stage freezes the exact evidence still required to convert direct hook flexion/extension physiology into a systematic-type identity crosswalk. It does not resolve polarity, does not authorize current calibration, and does not repeat the previously exhausted raw BANC/FANC acquisition route.

## Upstream state

NeuroFly already has two different evidence layers that must remain separate:

1. direct physiology establishes distinct flexion- and extension-sensitive hook populations and functional driver contexts;
2. connectome/circuit evidence supports the strong hypothesis that `SNpp39` is extension-associated and `SNpp41` is flexion-associated.

The second statement remains `PHYSIOLOGY_SUPPORTED_INFERENCE`, not a direct type-level physiology assignment.

PR #74 independently strengthened only the statement that current public BANC and MaleCNS annotation surfaces preserve `SNpp39` and `SNpp41` as FeCO hook systematic types. It did not resolve direction polarity.

## Direct functional driver anchors

Primary physiology sources provide direct directional labels for these driver contexts:

### Hook flexion

- `GMR21D12-GAL4`
- split driver: `VT038873-p65ADZ + R32H08-GAL4.DBD`

### Hook extension

- split driver: `VT018774-p65ADZ + VT040547-GAL4.DBD`

Sources:

- Neuron 2023: `https://doi.org/10.1016/j.neuron.2023.07.009`
- presynaptic-inhibition physiology resource: `https://pmc.ncbi.nlm.nih.gov/articles/PMC10634730/`

These functional labels are treated as direct physiology for the driver populations. They are **not** automatically systematic-type labels.

## New 2026 NeuronBridge capability

NeuronBridge software release 3.5.0 introduced expert-curated associations between Split-GAL4 lines and cell types. The UI exposes confidence, anatomical region, and source/annotator information, and the current frontend requests curated records through `/curated_matches`.

Reviewed software commit:

`18d97306372d27322482208432663f9f2b6b52a8`

Relevant software evidence:

- release notes: `https://github.com/JaneliaSciComp/neuronbridge/blob/18d97306372d27322482208432663f9f2b6b52a8/public/RELEASENOTES.md`
- search implementation: `https://github.com/JaneliaSciComp/neuronbridge/blob/18d97306372d27322482208432663f9f2b6b52a8/src/components/UnifiedSearch.jsx`
- confidence semantics: `https://github.com/JaneliaSciComp/neuronbridge/blob/18d97306372d27322482208432663f9f2b6b52a8/src/components/Help/HelpContents.jsx`

NeuronBridge defines `Confident` curated associations as greater than 95% confidence after detailed examination of potential associations. NeuroFly predeclares that only this highest level may satisfy this identity gate; `Probable`, `Candidate`, or a computed morphology score alone are insufficient.

## Current access result

The current NeuronBridge public landing/search surface requires user authentication to perform searches. In this audit run, no authenticated curated result for the exact hook driver contexts was obtained and no immutable exact-pair curated receipt was frozen.

This is recorded as **ACCESS_REQUIRED**, not as evidence that the curated database lacks the match.

Current public VFB pages do expose individual enhancer-component expression patterns and links into NeuronBridge. Those component-level surfaces do not prove the expression intersection of the exact split-GAL4 pair and therefore cannot establish systematic identity by themselves.

## Cross-dataset conflict guard

A morphology/computed NeuronBridge match is also insufficient because older public MANC annotation surfaces remain internally inconsistent with the newer BANC/MaleCNS hook identity evidence. Examples observed during this pass include:

- an `SNpp41` MANC record whose MANC/VFB surface is claw-classified: `https://www.virtualflybrain.org/term/snpp41_mesoln_l-manc177398-vfb_jrcv3svq/`
- an `SNpp39` MANC record whose surface is club-classified: `https://www.virtualflybrain.org/term/snpp39_metaln_r-manc44595-vfb_jrcv0yer/`

These conflicts are preserved rather than silently reconciled. They are not accepted as polarity evidence and are a reason to require an expert-curated, exact driver-to-cell-type bridge instead of promoting a raw morphology hit.

## Predeclared promotion requirements

Before `direct_crosswalk_found` can become true, NeuroFly requires an immutable receipt satisfying **all** of the following:

1. the record names the exact functional driver or an immutable identifier proven to represent that exact driver population;
2. the bridge is an expert-curated match, not only a computed morphology result;
3. confidence is `Confident`;
4. the record applies to the VNC anatomical context;
5. source or annotator provenance is present;
6. the target systematic type is exactly `SNpp39` or `SNpp41`;
7. both hook direction classes are independently covered;
8. flexion and extension form a pure one-to-one mapping to the two systematic types, with no mixing;
9. the assignments agree with the independent cross-dataset hook-identity gate from PR #74;
10. no conflicting curated assignment exists;
11. the complete evidence payload is frozen with an immutable receipt before promotion.

The gate must not be weakened after inspecting a future result.

## Current result

No direct identity promotion occurs here:

- `direct_bridge_receipt = null`
- `direct_crosswalk_found = false`
- `polarity_resolved = false`
- `SNpp39.direct_directional_tuning = null`
- `SNpp41.direct_directional_tuning = null`

The existing hypotheses remain unchanged:

- `SNpp39 ≈ extension-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`
- `SNpp41 ≈ flexion-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`

## Hard locks

- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `runtime_gating_authorized=false`
- `neural_payload_eligible=false`
- `promotion_ready=false`

This is an evidence/control-plane gate only. It changes no receptor encoding, neural payload, website state publication, systematic-type routing, current injection, stimulation, decoder, reward, or learning behavior.
