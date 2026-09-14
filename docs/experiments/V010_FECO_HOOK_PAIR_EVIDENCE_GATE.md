# V0.10 FeCO Hook-Pair Evidence Gate

Status: evidence candidate; current calibration and runtime stimulation remain blocked.

## Decision

NeuroFly now treats `SNpp39` and `SNpp41` as the complete currently evidence-backed MaleCNS FeCO hook pair, but it does **not** assign either systematic type to the `hook_extension` or `hook_flexion` neural channel.

The safe conclusion is:

```text
SNpp39 = FeCO hook type       ✅
SNpp41 = FeCO hook type       ✅
hook physiology is directional ✅
extension/flexion hook populations exist ✅
SNpp39 == extension or flexion ❌ unresolved
SNpp41 == extension or flexion ❌ unresolved
proprioceptive current calibration ❌ blocked
```

## Evidence layers

### 1. Functional physiology

Drosophila FeCO work establishes three major functional groups: claw neurons encode tibia position, hook neurons encode directional tibia movement, and club neurons encode bidirectional movement plus vibration. Later work further describes extension- and flexion-sensitive hook populations.

Relevant literature:

- Mamiya et al., *Neural coding of leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC6481666/
- Agrawal et al., *Central processing of leg proprioception in Drosophila*: https://elifesciences.org/articles/60299
- Chen et al., *Functional architecture of neural circuits for leg proprioception in Drosophila*: https://pmc.ncbi.nlm.nih.gov/articles/PMC8665017/

This evidence supports the current receptor-domain channels `hook_extension`, `hook_flexion`, `club_motion`, and `club_vibration`. It does not by itself map MaleCNS systematic type names to those tuning labels.

### 2. MaleCNS / VFB type identity

Virtual Fly Brain / MaleCNS classifications support:

- `SNpp39`: femoral chordotonal hook neuron
- `SNpp41`: femoral chordotonal hook neuron
- `SNpp58`: femoral chordotonal club neuron
- `SNpp59`: femoral chordotonal club neuron
- `SNpp60`: femoral chordotonal club neuron

Male CNS Cell Type Explorer independently lists `SNpp41` as `AKA: FeCO hook` and reports 22 neurons in `male-cns:v1.0`.

Relevant records:

- SNpp39: https://www.virtualflybrain.org/term/none-malecns810445-vfb_jrmc1721/
- SNpp41: https://www.virtualflybrain.org/term/none-malecns813147-vfb_jrmc1738/
- SNpp41 Cell Type Explorer: https://reiserlab.github.io/celltype-explorer-drosophila-male-cns/types/SNpp41.html
- SNpp58: https://www.virtualflybrain.org/term/none-malecns811808-vfb_jrmc17da/
- SNpp59: https://www.virtualflybrain.org/term/none-malecns908146-vfb_jrmc17dq/
- SNpp60: https://www.virtualflybrain.org/term/none-malecns812705-vfb_jrmc17dv/

### 3. Connectome organization

The systematic MANC annotation work identifies `SNpp39` and `SNpp41` as the two hook connectivity types and describes opposing predicted effects on tibia flexor/extensor motor circuits.

- reviewed preprint: https://elifesciences.org/reviewed-preprints/97766v1

The reviewed text supports distinct, opposing hook circuits. However, the evidence reviewed for this gate does **not** directly state which systematic type is the extension-sensitive sensory population and which is the flexion-sensitive population.

Motor-circuit sign is therefore not promoted into a sensory-tuning label by inference.

## MaleCNS exact-count gate

The prepared pinned MaleCNS audit must verify this exact candidate set:

| Type | Functional evidence class | Expected neurons |
| --- | --- | ---: |
| SNpp39 | hook direction candidate | 39 |
| SNpp41 | hook direction candidate | 22 |
| SNpp58 | club motion/vibration candidate | 16 |
| SNpp59 | club motion/vibration candidate | 6 |
| SNpp60 | club motion/vibration candidate | 41 |
| **Total** | | **124** |

Expected function totals:

- hook candidates: 61
- club candidates: 63

The overall pinned annotation totals remain:

- mechanosensory/proprioceptive: 1,454
- chordotonal organ: 425

Any count drift, missing type, class collision, or subclass collision fails the gate.

## Hard locks

`proprioception_feco_functional_crosswalk_v03.json` requires:

- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `directional_hook_identity_resolved=false`
- `current_calibration_authorized=false`
- `SNpp39.hook_direction_identity="unresolved"`
- `SNpp41.hook_direction_identity="unresolved"`

The loader rejects a crosswalk that changes either hook to `extension` / `flexion`, claims direction identity is resolved, or authorizes current calibration.

## Club limitation

`SNpp58`, `SNpp59`, and `SNpp60` are evidence-backed club types, but this gate also does not assign one club systematic type specifically to `club_motion` versus `club_vibration`. The current receptor contract may represent both channels, while direct MaleCNS current routing remains blocked until subtype evidence and calibration are defensible.

## What PASS means

A PASS means only:

1. the complete conservative hook pair is present in the pinned MaleCNS annotations;
2. the current conservative club candidates remain present;
3. their exact population counts match the frozen evidence expectation;
4. ambiguous direction identity remains unresolved by machine-enforced policy;
5. current calibration and runtime proprioceptive stimulation remain disabled.

A PASS does **not** authorize current amplitude selection, direction-specific hook stimulation, club subtype stimulation, six-leg routing, or behavioral claims.

## Next evidence gate

The next research stage is **hook direction identity disambiguation**. It should search primary physiology, MANC/BANC cross-dataset morphology, driver-line mappings, supplementary tables, or explicit curator aliases for a direct `SNpp39/SNpp41 -> extension/flexion` correspondence.

If no direct evidence is found, NeuroFly should keep direction-specific current disabled rather than infer the mapping from downstream motor effects.
