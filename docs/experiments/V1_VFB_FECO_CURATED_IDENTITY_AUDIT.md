# V1 VFB Curated FeCO Identity Audit

Status: **READ-ONLY EVIDENCE PROBE — NO POLARITY UNLOCK**

## New evidence target

PR #118 established a strong bidirectional morphology bridge between the
published hook-flexion driver `GMR21D12-GAL4` (NeuronBridge accession
`R21D12`) and MaleCNS `SNpp41:911942`, but computed morphology was not
accepted as curated identity.

A stronger public record now exists in Virtual Fly Brain:

- VFB term: `VFB_001028lx`
- native FANC / CATMAID id: `570810`
- label: R21D12 MCFO hook chordotonal neuron
- curated class: **prothoracic femoral chordotonal hook neuron**
- source: Phelps et al. FANC / FlyLight LM-to-EM identification

The unresolved question is whether VFB or a linked cross-reference explicitly
bridges this curated R21D12/FANC neuron to a MaleCNS `SNpp39` or `SNpp41`
identity.

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

1. an explicit curated FANC:570810 -> MaleCNS SNpp39/SNpp41 cross-reference;
2. an explicit directional `SNpp39 = extension / flexion` or
   `SNpp41 = extension / flexion` annotation;
3. an independently validated equivalent cell-level identity bridge.

Until then:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked
