# V1 Memory v/g + Delay Moderator Audit — Run 1

Status: **COMPLETE / FROZEN — EXPLORATORY DISCOVERY**

## Evidence integrity

- run: `36150726009`
- scientific head: `2e97523eb4789f0d3a832ae6369159de83871e19`
- artifact: `10873087880`
- artifact SHA-256: `0b835ae11a8eaf8b634ca392e3752944ec9218ac06fcd7927bad8ed6768c7a0b`
- receipt SHA-256: `59021b8dc34afba8225f5cc148805d40fb9e8c80f633f40df320ae2d89d780d1`
- source checkpoint unchanged: `e0830260a4e5c9c732537118037447183cd7c639c01f85a6c9d154fc6a03ae00`

Evidence-order integrity was preserved:

- selection manifest was written before effect evaluation
- pre-intervention feature manifest was written before effect evaluation
- no feature-ranking threshold was used during execution
- all eight selected histories have unique pre-event checkpoint and sensory-sequence digests

## Effect labels

Fresh cohort:

- suppression: **6/8**
- reversal: **1/8**
- mixed: **1/8**

This independently preserves the key finding from #160:

**the effect of clearing v/g + refractory/delay is strongly history dependent.**

## Aggregate neural expression

| Condition | changed-KC | changed-edge L1 | MBON07 state |
|---|---:|---:|---:|
| intact | 0.263250 | 0.388355 | 0.761905 |
| v/g + delay clear | 0.118930 | 0.177166 | 0.363095 |

Aggregate suppression remains strong, but the history labels show it is not universal.

## Strongest exploratory moderator family

The clearest pre-intervention signal is **boundary adaptation engagement**.

Lead feature:

`adaptation.paired_mean.std`

Suppression histories:

- MA1: 1.088255
- MA2: 1.086583
- MA4: 1.089218
- MA6: 1.132786
- MA7: 1.115099
- MA8: 1.109288

Non-suppression histories:

- MA3 / mixed: 0.054963
- MA5 / reversal: 0.052096

Group means:

- suppression: **1.103538**
- non-suppression: **0.053530**

Exploratory standardized mean difference: **86.69**.

The same separation appears across the adaptation family:

- `adaptation.true.std`: SMD 92.49
- `adaptation.paired_mean.mean`: SMD 69.79
- `adaptation.paired_mean.nonzero_fraction`: SMD 51.29
- `adaptation.paired_mean.max_abs`: SMD 29.21

This makes **adaptation engagement** the strongest discovery-derived moderator candidate.

## Important correlated signal

Both non-suppression histories also had:

- lag -21 changed-KC active fraction = 0
- lag -21 changed-edge L1 engagement = 0

All six suppression histories had nonzero values at lag -21.

Therefore the current data do **not** establish whether adaptation state itself
is mechanistically responsible, whether immediate prefix expression is the
more proximal moderator, or whether both reflect a common upstream state.

## Interpretation boundary

Supported:

**High boundary adaptation engagement is an exploratory candidate marker for
whether v/g+delay clearing suppresses stored-memory expression.**

Not supported:

- adaptation is a confirmed moderator
- adaptation is causal
- adaptation is the transient memory carrier
- the discovered separation will generalize to a new cohort

## Next clean step

Use a fresh outcome-blind cohort and preregister the discovery-derived
adaptation gap before effect labels are computed.

A gap-based validation can classify:

- adaptation-quiescent: `adaptation.paired_mean.std <= 0.10`
- adaptation-engaged: `adaptation.paired_mean.std >= 0.50`
- intermediate: values between those bands, reported but not forced into either group

The validation hypothesis should be:

- engaged histories are expected to show the all-three-endpoint suppression pattern more often than quiescent histories.

This next study must remain independent of the present exploratory cohort.

## Governance

Still false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `moderator_confirmed`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

No production checkpoint or model parameter was changed.
