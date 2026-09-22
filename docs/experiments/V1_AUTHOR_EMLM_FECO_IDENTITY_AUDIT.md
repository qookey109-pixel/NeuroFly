# V1 Phelps/GridTape Author EM-LM FeCO Identity Audit

Status: **READ-ONLY EVIDENCE PROBE — NO POLARITY UNLOCK**

## Why this layer exists

PR #119 froze the provenance correction that `VFB_001028lx / 570810` is an
R21D12 light-microscopy reference registered into FANC/CATMAID space, not a
unique FANC EM-cell identity.

The next question is narrower:

`R21D12 LM reference -> specific FANC EM hook cell ?`

This audit does **not** recompute morphology. It reads the Phelps/GridTape
author artifacts used for Figure 4, *Sensory neuron subtypes and EM-LM
correspondence*.

## Pinned author artifacts

Repository: `htem/GridTape_VNC_paper`

Commit: `5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9`

The author code loads:

`catmaid_nblast_scores_id93_LMxEM_leftT1_sensoryNeurons.csv`

and stores the top five EM hits for non-bCS LM sensory neurons.

The checked-in R21D12 result is:

- R21D12 atlas/project59 skeleton: `570806`
- top 1: `515392` — NBLAST `0.508957`
- top 2: `515366` — NBLAST `0.494256`
- top 3: `515458` — NBLAST `0.473981`
- top 4: `511045` — NBLAST `0.468952`
- top 5: `515617` — NBLAST `0.464603`

The author's project59 chordotonal subtype JSON assigns all five to the hook
color `#7e2f8e`; the author's utility maps that color to
`T1 leg hook chordotonal neuron`.

Thus the author-generated LM->EM analysis independently supports that the
R21D12 reference lies inside the hook EM population. It does not by itself
select one EM cell as curated identity.

## Cell-level recovery

The author transformation utility documents a stronger identity mechanism.
Transformed project59 neurons receive a linking annotation of the form:

`LINKED NEURON - elastic transformation of skeleton id <source> in project id 2 ...`

The probe queries CATMAID's public:

`POST /59/annotations/forskeletons`

for each author top-five project59 skeleton and, when available, recovers the
original FANC project2 skeleton ID and neuron name.

The legacy author CATMAID server still exposes project59 neuron names such as
`... (neuron 25849) - elastic transform`. When the linking-annotation endpoint
is not publicly readable, that server-side neuron name is used only to recover
the source ID. The source ID is then independently verified against the pinned
author file
`neuron_reconstructions/skeletons_in_FANC_space/sensory_neurons_annotations.json`.
A valid recovery must resolve to exactly one author-annotated left-T1 hook
sensory neuron.

Observed author top-five mapping:

- `515392 -> FANC 25849`
- `515366 -> FANC 25842`
- `515458 -> FANC 25856`
- `511045 -> FANC 24831`
- `515617 -> FANC 25909`

All five recovered source IDs are present in the pinned FANC-space author
annotation file as left-T1 hook chordotonal sensory neurons.

This recovers the **source FANC identities of the five transformed top-hit
neurons**, but it still does not turn the rank-1 morphology hit into a curated
one-to-one R21D12 identity. No positional/order matching between project2 and
project59 JSON files is accepted.

## Downstream gate

The already frozen downstream target remains:

`MaleCNS 911942 -> MANC 97015 -> SNpp41`

Even a successful R21D12->FANC EM source recovery does **not** establish the
missing curated FANC->MANC/SNpp41 identity edge.

Therefore this audit never changes:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked
