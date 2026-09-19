# V1 VFB Curated FeCO Identity Audit

Status: **READ-ONLY EVIDENCE PROBE — NO POLARITY UNLOCK**

## New evidence target

PR #118 established a strong bidirectional morphology bridge between the
published hook-flexion driver `GMR21D12-GAL4` (NeuronBridge accession
`R21D12`) and MaleCNS `SNpp41:911942`, but computed morphology was not
accepted as curated identity.

A stronger public record now exists in Virtual Fly Brain:

- VFB term: `VFB_001028lx`
- VFB/CATMAID registration accession: `570810`
- label: R21D12 MCFO hook chordotonal neuron
- curated class: **prothoracic femoral chordotonal hook neuron**
- source: Phelps et al. FANC / FlyLight LM-to-EM identification

The unresolved question is whether VFB or a linked cross-reference explicitly
bridges this curated R21D12 reference to a specific FANC EM hook cell and then
to a MaleCNS/MANC `SNpp39` or `SNpp41` identity.

## Provenance correction: 570810 is not a unique FANC EM body

The Phelps/GridTape author repository distinguishes two kinds of records in the
same sensory-neuron annotation inventory:

- the `R21D12 MCFO F2` hook reference is explicitly marked
  `tracing from light microscopy` and registered into the common/FANC space;
- reconstructed FANC hook cells are separate records explicitly marked
  `tracing from electron microscopy`, with individual neuron IDs such as
  right-T1 `16760`, `16582`, `16755`, `16682`, `16705`, and `17665`.

Therefore `VFB_001028lx / 570810` is strong curated evidence for **R21D12 =
hook morphology/type**, but must not be interpreted as a one-to-one FANC EM
cell identity. The missing cell-level edge is now defined as:

`R21D12 LM reference -> specific FANC EM hook cell -> MANC/MaleCNS SNpp type`.

Author-source provenance:

- `htem/GridTape_VNC_paper`
- commit `5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9`
- `neuron_reconstructions/skeletons_in_JRC2018_VNC_FEMALE_space/sensory_neurons_annotations.json`

## New exact MaleCNS -> MANC bridge recovered

The public MaleCNS v1 DVID annotation contains explicit MANC fields. In
particular, the current strongest frozen SNpp41 target resolves as:

- MaleCNS `911942` -> `mancBodyid = 97015`
- `mancType = SNpp41`

This makes the MaleCNS -> MANC half of the identity chain explicit. It does not
supply the missing R21D12/FANC-EM -> MANC edge and therefore does not unlock
polarity.

## Data source

The probe uses VFB's public read-only **VFBquery API**:

`https://v3-cached.virtualflybrain.org`

No token or account is required.

Queries include:

- `search(SNpp39)`
- `search(SNpp41)`
- `search(R21D12 / GMR21D12 / 570810)`
- `get_term_info(VFB_001028lx)`
- `xref(VFB_001028lx)`
- `xref(accession=570810)`
- term-info lookups for frozen MaleCNS SNpp39/SNpp41 bodies

## Decision rule

A curated R21D12/FANC hook label alone does **not** establish SNpp polarity.

Unlock requires at least one of:

1. an explicit curated R21D12 LM -> specific FANC EM hook cell -> MaleCNS/MANC SNpp39/SNpp41 bridge;
2. an explicit directional `SNpp39 = extension / flexion` or
   `SNpp41 = extension / flexion` annotation;
3. an independently validated equivalent cell-level identity bridge.

Until then:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked
