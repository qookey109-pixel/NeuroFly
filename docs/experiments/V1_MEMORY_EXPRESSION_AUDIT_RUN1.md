# V1 Reward Memory Expression Audit — Run 1

## Status

**EXPLORATORY EXPRESSION AUDIT COMPLETE**

Successful GitHub Actions run: `36095246269`

- artifact id: `10847815197`
- artifact digest: `sha256:96196df2069176c49c29676a9eac7e1d60e36439a9fa33cfa5260e363a04de13`
- receipt digest: `a44838d604a8f277b877bcd8195ff69604b9d0f35cdb8b45bf1270dff0b9bbca`
- source checkpoint: `067f4897fd50eeb011865c18898f47184721f81e3866774bbe68a78478f481c9`

The production checkpoint was unchanged. All preregistration and evidence gates
passed.

## Core result

Across all four fresh-seed replicates, the paired reward-memory state contained:

- **1,522 changed KC→MBON07 edges**
- **768 unique presynaptic KCs**

During state-cleared replay of the exact reward-event cue:

- active changed presynaptic KCs: **0 / 768**
- changed edges with an active presynaptic KC: **0 / 1,522**
- paired reward-memory L1 carried on active presynaptic edges: **0%**
- weighted changed-edge presynaptic-drive proxy: **0**

Thus the stored synaptic difference was present, but the single recall cue did
not presynaptically engage it.

## MBON07 expression

The four MBON07 body IDs were:

- 12859
- 15626
- 18603
- 515338

For both paired branches, all four MBON07s produced zero spikes during the
state-cleared recall cue.

Paired differences were also exactly zero for:

- MBON07 total spikes
- MBON07 membrane potential
- MBON07 conductance

## Downstream decoder

No paired difference was detected in:

- DNp20 left/right spike output
- DNp20 membrane potential
- DNpe017 spike output
- DNpe017 membrane potential
- decoded action

Action divergence was **0 / 4**.

## Interpretation

This audit narrows the current bottleneck upstream of MBON07 expression.

It does **not** show that a changed KC→MBON07 memory reaches MBON07 and is then
lost downstream. Instead, under the exact single state-cleared reward cue, none
of the 768 presynaptic KCs carrying the paired memory difference spiked.

The operational chain is therefore:

`persistent KC→MBON07 synaptic difference`
→ **changed-KC ensemble not reactivated by single reward cue**
→ MBON07 difference = 0
→ decoder difference = 0
→ action difference = 0

This is strong localization evidence under this assay, but
`cue_indexing_failure_confirmed` remains false because the model's plasticity
rule contains temporal KC eligibility. The learned index may correspond to a
pre-reward sensory sequence rather than the instantaneous reward-event frame.

## Next preregistered question

Audit the frozen temporal eligibility window without changing parameters:

1. record KC activity for the fixed sequence preceding the first natural reward;
2. identify when the 768 changed-edge presynaptic KCs were active;
3. quantify overlap between changed-edge KCs and KC activity at each lag;
4. state-clear both paired branches;
5. replay the same prereward sequence, still with plasticity frozen and no
   reinforcement;
6. measure whether the sequence re-engages changed KCs and produces MBON07
   expression.

Only after this temporal-index question is resolved should downstream decoder
or behavioral confirmation be reconsidered.

## Claim state

All remain false:

- `learning_validated`
- `memory_expression_causal`
- `cue_indexing_failure_confirmed`
- `downstream_readout_failure_confirmed`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
