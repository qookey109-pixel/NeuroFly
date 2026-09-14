# V0.11 SNpp39 / SNpp41 Tuning Evidence Audit

Status: **REVIEW_REQUIRED / direction polarity unresolved**. This is a read-only biological evidence gate. No proprioceptive current or stimulation is authorized.

## Why this gate exists

The preceding morphology audit showed that MaleCNS body `905407` lies inside a peer-derived `SNpp41` coarse morphology envelope. Morphology cannot determine whether a proprioceptor is flexion-encoding or extension-encoding, so NeuroFly requires an independent biological tuning crosswalk before any sensory current can be calibrated.

## Evidence supported by current literature and curated resources

### FeCO functional organization

Adult Drosophila femoral chordotonal organ (FeCO) neurons are divided into functional/anatomical populations:

- claw neurons encode femur-tibia joint position;
- hook neurons encode directional tibia movement;
- club neurons encode bidirectional movement and low-amplitude/high-frequency vibration.

Physiology further resolves hook neurons into distinct **flexion-encoding** and **extension-encoding** populations.

Primary/reviewed sources used by this audit include:

- Mamiya et al., *Neural coding of leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC6481666/
- Chen et al., *Functional architecture of neural circuits for leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC8665017/
- Dinges et al., *Biomechanical origins of proprioceptor feature selectivity and topographic maps in the Drosophila leg*: https://doi.org/10.1016/j.neuron.2023.07.009
- *Divergent neural circuits for proprioceptive and exteroceptive sensing of the Drosophila leg*: https://www.nature.com/articles/s41467-025-59302-3

### SNpp39 / SNpp41 systematic-type evidence

The systematic adult male VNC annotation describes `SNpp39` and `SNpp41` as FeCO-related proprioceptive types and predicts that the two hook pathways exert opposing effects on tibia extensor versus flexor motor circuits. That is consistent with the existence of opposing directional hook pathways, but circuit sign alone is not used to assign sensory direction.

Source:

- *Systematic annotation of a complete adult male Drosophila nerve cord connectome reveals principles of functional organisation*: https://elifesciences.org/reviewed-preprints/97766v1

Curated/public VFB evidence also supports hook-related identity, for example:

- MaleCNS `SNpp39`, body `810445`, VFB `VFB_jrmc1721`: https://www.virtualflybrain.org/term/none-malecns810445-vfb_jrmc1721/
- BANC `SNpp39` example: https://www.virtualflybrain.org/term/banc_626720575941626274698-vfb_001053oz/
- BANC `SNpp41` example: https://www.virtualflybrain.org/term/banc_626720575941503646514-vfb_00105x02/

## Annotation caveat

Cross-dataset public annotations are not perfectly uniform. Some MANC VFB examples attach `club` to `SNpp39` or `claw` to `SNpp41`, whereas MaleCNS/BANC examples and the systematic connectome analysis support hook-related assignments. These conflicts are preserved rather than silently normalized away.

Examples:

- MANC `SNpp39` example labelled FeCO club: https://www.virtualflybrain.org/term/snpp39_metaln_r-manc44595-vfb_jrcv0yer/
- MANC `SNpp41` example labelled FeCO claw: https://www.virtualflybrain.org/term/snpp41_metaln_r-manc28960-vfb_jrcv0mcg/
- another MANC `SNpp41` record has hook subclass text: https://www.virtualflybrain.org/term/snpp41_metaln_r-manc36039-vfb_jrcv0rt3/

Therefore NeuroFly does not use a single legacy label as a direction-polarity crosswalk.

## Current unresolved point

The evidence inspected in this gate does **not** provide an explicit experimentally validated statement that maps the systematic types to movement polarity, e.g.:

- `SNpp39 = flexion-encoding hook` or `SNpp39 = extension-encoding hook`;
- `SNpp41 = flexion-encoding hook` or `SNpp41 = extension-encoding hook`.

The connectome paper predicts opposing effects on flexor/extensor motor circuits, but assigning the sensory polarity from the sign of a predicted reflex circuit would be an inference. NeuroFly does not accept that as ground truth.

## Frozen decision boundary

Supported:

- `SNpp39 / SNpp41` are proprioceptive FeCO-related systematic types;
- hook neurons are directional movement encoders;
- hook physiology contains flexion-encoding and extension-encoding populations;
- `SNpp39` and `SNpp41` participate in opposing predicted motor pathways.

Not yet supported strongly enough:

- exact `SNpp39 ↔ flexion/extension` polarity;
- exact `SNpp41 ↔ flexion/extension` polarity.

Forbidden without new explicit evidence:

- `SNpp39=flexion`
- `SNpp39=extension`
- `SNpp41=flexion`
- `SNpp41=extension`
- polarity inferred from morphology alone
- polarity inferred from predicted motor/reflex sign alone

## Hard locks

Until an explicit systematic-type-to-direction crosswalk is found and separately audited:

- `systematic_type_direction_polarity_resolved=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `promotion_ready=false`

A `REVIEW_REQUIRED` result here is therefore the correct conservative outcome, not a failed morphology result.
