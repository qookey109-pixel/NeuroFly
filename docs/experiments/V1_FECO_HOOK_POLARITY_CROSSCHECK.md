# V1 FeCO Hook Polarity Crosscheck

Status: **EVIDENCE CROSSCHECK ONLY — POLARITY GATE REMAINS LOCKED**

This note records a new evidence route for the unresolved NeuroFly
`SNpp39` / `SNpp41` FeCO hook polarity problem.

It deliberately does **not** reuse the previously exhausted BANC metadata /
matching-table route and does not authorize runtime stimulation.

## Question

Which MaleCNS systematic hook type corresponds to the experimentally defined
FeCO hook movement directions?

- hook flexion
- hook extension

The unresolved systematic types are:

- `SNpp39`
- `SNpp41`

## What is directly supported

Current Virtual Fly Brain MaleCNS annotations classify both systematic types as
femoral chordotonal hook neurons:

- SNpp39 example: MaleCNS:903843
  - https://www.virtualflybrain.org/term/none-malecns903843-vfb_jrmc171p/
- SNpp41 example: MaleCNS:813147
  - https://www.virtualflybrain.org/term/none-malecns813147-vfb_jrmc1738/

This supports hook identity, but these pages do not state flexion versus
extension polarity.

## New route: signed premotor circuit crosscheck

Marin et al., *Systematic annotation of a complete adult male Drosophila nerve
cord connectome reveals principles of functional organisation*:

- eLife reviewed preprint: https://elifesciences.org/reviewed-preprints/97766
- DOI: 10.7554/eLife.97766.1
- bioRxiv DOI: 10.1101/2023.06.05.543407

The reconstructed MANC premotor circuit gives the two systematic hook types
opposing motor signs:

### SNpp41

The paper predicts that SNpp41:

- inhibits the tibia flexor motor neuron;
- inhibits the accessory tibia flexor motor neuron through GABAergic
  `IN19A015`;
- activates the tibia extensor motor neuron.

### SNpp39

The paper predicts that SNpp39:

- inhibits the tibia extensor motor neuron through GABAergic `IN19A005`;
- `IN19A005` also inhibits `IN19A015`;
- this disinhibits the tibia flexor and accessory tibia flexor motor neurons.

The authors explicitly summarize these two hook types as having opposing
effects on tibia extensor versus flexor muscles and state that this is
consistent with their observed responses to directional tibia movement.

## Functional direction anchor

Chen et al., *Functional architecture of neural circuits for leg
proprioception in Drosophila*:

- Current Biology 31 (2021), 5163-5175.e7
- DOI: 10.1016/j.cub.2021.09.035
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8665017/

Chen et al. directly distinguish the light-level functional hook channels:

- `8Aa` responds to hook **flexion** input;
- `13Bb` responds to hook **extension** input;
- EM reconstruction shows direct input from hook-extension axons to 13Bb;
- 13Bb responds during tibia extension.

The same paper interprets these proprioceptive circuits in the context of
resistance reflexes that oppose perturbations.

Agrawal et al., *Central processing of leg proprioception in Drosophila*:

- eLife 9:e60299
- DOI: 10.7554/eLife.60299
- https://elifesciences.org/articles/60299

provides an experimentally observed sign anchor: 13Ba neurons encode tibia
extension, while activation of 13Ba drives femur-tibia **flexion**.

That is consistent with an extension sensory representation producing an
opposing flexion motor response in a resistance-reflex pathway.

## Candidate crosswalk

Combining the signed MANC motor effects with the resistance-reflex sign gives
the following **candidate**, not a direct annotation:

| MaleCNS type | MANC predicted motor effect | Resistance-reflex-consistent sensory direction | Status |
| --- | --- | --- | --- |
| `SNpp39` | inhibit extensor; disinhibit flexors | sensed **extension** | **hook extension candidate** |
| `SNpp41` | inhibit flexors; activate extensor | sensed **flexion** | **hook flexion candidate** |

Interpretation:

- if the leg is moving/extending, an opposing resistance response is flexion;
  SNpp39 has that premotor sign;
- if the leg is moving/flexing, an opposing resistance response is extension;
  SNpp41 has that premotor sign.

This is a **strong circuit-consistency inference**.

It is **not** equivalent to finding a source that explicitly states
`SNpp39 = hook extension` and `SNpp41 = hook flexion`.

## Why the gate remains locked

No reviewed source located in this crosscheck directly binds the systematic
MANC/MaleCNS labels `SNpp39` and `SNpp41` to Chen's light-level
hook-extension / hook-flexion driver identities.

The 13B versus 14A downstream-lineage relationship is also **not** treated as a
decisive crosswalk. Dataset/annotation differences and the lack of an explicit
type-to-functional-identity statement make that route insufficient for exact
runtime polarity.

Therefore:

- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- `current_calibration_authorized = false`
- `runtime_stimulation_authorized = false`

## What would unlock the gate

At least one independently auditable source must explicitly provide one of:

1. a systematic type annotation that labels SNpp39/SNpp41 as
   hook-extension/hook-flexion;
2. a cross-dataset neuron match that explicitly maps the systematic types to
   Chen's directional hook identities;
3. an equivalent primary-data mapping whose transformation can be reproduced
   and audited.

Until then, NeuroFly may preserve the candidate crosswalk for research
navigation, but must not use it for exact Current Calibration or runtime
stimulation.

Machine-readable state:

`data/feco_hook_polarity_crosscheck_v01.json`
