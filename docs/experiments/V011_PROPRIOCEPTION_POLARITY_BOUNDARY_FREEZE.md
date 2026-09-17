# V0.11 Proprioception — SNpp39/SNpp41 Polarity Boundary Freeze

## Purpose

Freeze the current evidence boundary for the FeCO hook flexion/extension crosswalk after exhausting the currently available direct public evidence lanes, without promoting a circuit-level inference into a biological type-level fact.

## Upstream stack

This audit is stacked directly on Draft PR #78 at exact head:

`c8d4e7ace04d75dc0e9e696b8b5826fc67c73092`

## Primary physiology anchor

Mamiya et al., Neuron 2023:

`https://doi.org/10.1016/j.neuron.2023.07.009`

The paper directly identifies the functional driver populations:

- hook flexion: `VT038873-p65ADZ + R32H08-GAL4.DBD`
- hook extension: `VT018774-p65ADZ + VT040547-GAL4.DBD`

The paper and its supplement do not provide an explicit `SNpp39` / `SNpp41` systematic-type label for those two functional driver populations.

## Systematic annotation anchor

MaleCNS systematic annotation:

`https://elifesciences.org/reviewed-preprints/97766`

The systematic annotation supports `SNpp39` and `SNpp41` as proprioceptive FeCO hook types. It also supports a strong connectivity-based directional interpretation, but does not state a direct author-level functional-driver-to-systematic-type flexion/extension crosswalk.

## Authenticated NeuronBridge UI observations

A normal authorized NeuronBridge user session was used to inspect expert-curated matches. No password, token, cookie, Authorization header, JWT, or other credential is stored in this repository.

### SNpp39

Observed curated VNC match:

- `SS57886`
- confidence: `Confident`
- region: `vnc`
- annotator: `Claire Managan`
- cell type: `SNpp39`

The public Split-GAL4 line page identifies `SS57886` as:

- AD: `R23G05-p65ADZp`
- DBD: `R41A08-ZpGdbd`

Therefore the `Confident` identity evidence is useful for `SS57886 -> SNpp39`, but it does **not** establish equivalence to either physiology hook driver pair.

### SNpp41

The authenticated curated query showed five VNC `Candidate` matches and zero `Confident` matches:

- `SS00359`
- `SS02407`
- `SS45467`
- `SS46317`
- `SS58881`

These Candidate annotations are not promotion evidence under the predeclared NeuroFly gate.

## Why the polarity remains unresolved

The two strong evidence halves still do not overlap at an exact type-level bridge:

1. direct physiology resolves hook flexion versus hook extension for exact functional driver populations;
2. systematic annotation and curated identity data resolve SNpp39/SNpp41 as hook-related systematic types;
3. no exact immutable evidence currently connects both physiology driver populations to SNpp39/SNpp41.

Therefore the best supported mapping remains:

- `SNpp39 ~= extension`
- `SNpp41 ~= flexion`

with strength:

`PHYSIOLOGY_SUPPORTED_INFERENCE`

This is intentionally **not** promoted to a direct crosswalk.

## Promotion requirement

Promotion requires one of the following:

1. an explicit author source mapping hook flexion/extension directly to `SNpp39`/`SNpp41`;
2. an exact independently validated functional-driver-to-systematic-type morphology or curated identity crosswalk with immutable receipt covering both hook directions;
3. equivalent direct type-level evidence covering both directions.

NeuronBridge `Candidate` annotations, raw morphology similarity, circuit sign inference, a `Confident` unrelated Split-GAL4 identity, or legacy MANC claw/club subclass labels do not satisfy this requirement.

## Frozen state

`FROZEN_PENDING_DIRECT_TYPE_LEVEL_EVIDENCE`

The following remain false:

- `direct_crosswalk_found`
- `polarity_resolved`
- `current_calibration_authorized`
- `stimulation_enabled`
- `runtime_transduction_enabled`
- `runtime_gating_authorized`
- `systematic_type_mapping_exposed`
- `neural_payload_eligible`
- `promotion_ready`

This freeze is a science boundary, not an assertion that the current inference is wrong. New direct evidence may support or overturn the current mapping and must be reviewed without changing the gate after seeing the result.
