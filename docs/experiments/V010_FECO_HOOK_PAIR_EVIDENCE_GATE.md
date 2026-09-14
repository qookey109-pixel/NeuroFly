# V0.10 FeCO Hook-Pair Evidence Gate

Status: **REVIEW_REQUIRED** evidence gate; current calibration and runtime stimulation remain blocked.

## Decision

Literature and MaleCNS type-level resources support `SNpp39` and `SNpp41` as the FeCO hook pair. However, the pinned MaleCNS v1.0 annotation audit found that `SNpp41` is not a clean exact-type stimulation population:

- `SNpp39`: 39 mechanosensory/proprioceptive + chordotonal-organ rows;
- `SNpp41`: 21 mechanosensory/proprioceptive + chordotonal-organ rows;
- `SNpp41`: **1 additional mechanosensory/proprioceptive row with subclass `leg`**;
- `SNpp58`: 16 clean chordotonal-organ rows;
- `SNpp59`: 6 clean chordotonal-organ rows;
- `SNpp60`: 41 clean chordotonal-organ rows.

The safe conclusion is therefore:

```text
SNpp39 = clean FeCO hook candidate                 ✅
SNpp41 = FeCO hook at type/literature level        ✅
SNpp41 = clean exact-type stimulation population   ❌ REVIEW_REQUIRED
hook physiology is directional                     ✅
extension/flexion hook populations exist           ✅
SNpp39 == extension or flexion                     ❌ unresolved
SNpp41 == extension or flexion                     ❌ unresolved
proprioceptive current calibration                 ❌ blocked
runtime proprioceptive stimulation                 ❌ blocked
```

NeuroFly does **not** relax the subclass gate to absorb the one `SNpp41|leg` row. The exception is frozen as evidence and remains unselected/not stimulated.

## Prepared evidence

The authoritative runtime receipt is GitHub Actions run `34804436631` against pinned Stonkfly commit `78ef3e05ab0fa086032098558d893667068944a0` and prepared MaleCNS v1.0.

The prepared graph reported:

- retained neurons: 166,700;
- directed edges: 25,582,938;
- mechanosensory/proprioceptive neurons: 1,454;
- chordotonal-organ neurons: 425;
- selected conservative FeCO rows: 123;
- unresolved proprioceptive rows: 1,331.

Selected rows:

| Type | Evidence class | Accepted chordotonal rows | Other same-type rows | Status |
| --- | --- | ---: | ---: | --- |
| SNpp39 | hook direction candidate | 39 | 0 | clean candidate |
| SNpp41 | hook direction candidate | 21 | 1 × `leg` | **REVIEW_REQUIRED** |
| SNpp58 | club motion/vibration candidate | 16 | 0 | clean candidate |
| SNpp59 | club motion/vibration candidate | 6 | 0 | clean candidate |
| SNpp60 | club motion/vibration candidate | 41 | 0 | clean candidate |

Function totals among accepted chordotonal rows:

- hook candidates: 60 (`SNpp39` 39 + `SNpp41` 21);
- club candidates: 63;
- total: 123.

Only 102 selected rows belong to types currently marked `clean_candidate`; the 21 accepted SNpp41 chordotonal rows remain attached to a `review_required_mixed_subclass` type and are **not authorized for stimulation**.

## Evidence layers

### 1. Functional physiology

Drosophila FeCO studies support three broad functional groups: claw neurons encode tibia position, hook neurons encode directional tibia movement, and club neurons encode bidirectional motion/vibration. Later work describes extension- and flexion-sensitive hook populations.

Relevant literature:

- Mamiya et al., *Neural coding of leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC6481666/
- Agrawal et al., *Central processing of leg proprioception in Drosophila*: https://elifesciences.org/articles/60299
- Chen et al., *Functional architecture of neural circuits for leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC8665017/

This supports NeuroFly's receptor-domain `hook_extension`, `hook_flexion`, `club_motion`, and `club_vibration` channels. It does not directly map MaleCNS systematic type names to those tuning labels.

### 2. MaleCNS type-level identity

Current type-level resources support:

- `SNpp39`: FeCO hook candidate;
- `SNpp41`: FeCO hook candidate;
- `SNpp58/59/60`: FeCO club candidates.

Male CNS Cell Type Explorer lists `SNpp41` as `AKA: FeCO hook` and reports 22 neurons at the type level. The prepared NeuroFly annotation audit resolves those 22 rows as 21 chordotonal-organ rows plus one `leg`-subclass row. Type-level identity therefore does not override row-level runtime annotation gates.

Relevant records:

- SNpp39: https://www.virtualflybrain.org/term/none-malecns810445-vfb_jrmc1721/
- SNpp41: https://www.virtualflybrain.org/term/none-malecns813147-vfb_jrmc1738/
- SNpp41 Cell Type Explorer: https://reiserlab.github.io/celltype-explorer-drosophila-male-cns/types/SNpp41.html
- SNpp58: https://www.virtualflybrain.org/term/none-malecns811808-vfb_jrmc17da/
- SNpp59: https://www.virtualflybrain.org/term/none-malecns908146-vfb_jrmc17dq/
- SNpp60: https://www.virtualflybrain.org/term/none-malecns812705-vfb_jrmc17dv/

### 3. Connectome organization

The systematic MANC annotation work identifies `SNpp39` and `SNpp41` as two hook connectivity types and describes opposing predicted effects on tibia flexor/extensor motor circuits:

- https://elifesciences.org/reviewed-preprints/97766v1

That supports distinct hook circuits, but the reviewed evidence does **not** directly state which systematic type is the extension-sensitive sensory population and which is the flexion-sensitive population.

NeuroFly therefore does not infer sensory tuning identity from downstream motor sign.

### 4. Cross-dataset annotation caution

Older MANC/VFB individual records show inconsistent club/claw/hook labels for some `SNpp39`/`SNpp41` entries. This is another reason to keep runtime selection tied to the pinned MaleCNS audit and to avoid deriving extension/flexion identity from historical labels alone.

## Machine-enforced REVIEW_REQUIRED contract

`data/proprioception_feco_functional_crosswalk_v03.json` requires:

- `promotion_status="review_required"`;
- `promotion_ready=false`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`;
- `directional_hook_identity_resolved=false`;
- `current_calibration_authorized=false`;
- `SNpp39.hook_direction_identity="unresolved"`;
- `SNpp41.hook_direction_identity="unresolved"`;
- `SNpp41.mapping_status="review_required_mixed_subclass"`;
- exactly one frozen annotation exception: `SNpp41|leg = 1`, disposition `review_required_not_selected_not_stimulated`.

The audit fails if the known exception disappears, changes count, changes subclass, or if any new mapped-type collision appears. A green workflow therefore means the frozen REVIEW_REQUIRED evidence receipt reproduced exactly; it does **not** mean the population was promoted.

## Club limitation

`SNpp58`, `SNpp59`, and `SNpp60` are clean evidence-backed club candidates, but this gate does not assign the systematic types specifically to `club_motion` versus `club_vibration`. Direct MaleCNS current routing remains blocked until subtype evidence and calibration are defensible.

## What a green audit means

A successful audit means only:

1. the pinned dataset still reproduces the exact known SNpp41 mixed-subclass exception;
2. `SNpp39`, `SNpp58`, `SNpp59`, and `SNpp60` remain clean under the frozen gates;
3. the 21 SNpp41 chordotonal rows remain visible for evidence review but unpromoted;
4. extension/flexion identity remains unresolved;
5. current calibration/runtime stimulation remain blocked.

It does **not** authorize current amplitude selection, SNpp41 stimulation, direction-specific hook stimulation, club subtype stimulation, six-leg routing, or behavioral claims.

## Next evidence gate

Two research-only questions remain before current calibration can even be considered:

1. **SNpp41 annotation exception audit** — identify the exact body/instance associated with the single `SNpp41|leg` row and determine whether it represents annotation drift, a legitimate mixed systematic type, or another issue. Do not discard it merely to obtain a clean type.
2. **Hook direction identity disambiguation** — find direct primary/supplementary/cross-dataset evidence for `SNpp39/SNpp41 -> extension/flexion` sensory tuning. Downstream motor effects alone are insufficient.

Until both gates are resolved conservatively, proprioceptive current stays off.
