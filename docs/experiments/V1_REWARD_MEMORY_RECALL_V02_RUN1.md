# V1 Reward Memory Recall V0.2 — Run 1

## Status

**EXPLORATORY RECALL COMPLETE**

Successful GitHub Actions run: `36094504041`

- artifact id: `10847430494`
- artifact digest: `sha256:be99048d5feb253e65418dbaedd8f3eff49be6f5e5e5abd9c68a937fd13febfc`
- receipt digest: `79eda0b1cf440e7e7bbe99233784b01789d010e16e136128dd8cdbbbe3431ca3`
- source checkpoint: `331a9a32ba39ec38bd205297ce28ae42467ad661b3b87ac6ab4435d2cc23b1ab`

The production checkpoint was unchanged before/after execution.

## V0.1 boundary

V0.1 remains invalid and is not used as evidence. Its fixed 60-decision
acquisition rule failed feasibility under the then-current production
checkpoint. V0.2 used new seeds and the separately preregistered event-triggered
acquisition rule.

## Execution integrity

All config and evidence gates passed.

All four fresh V0.2 trajectories were distinct by trajectory digest.

For each replicate:

- first natural reward occurred at recorded decision index **3**;
- acquisition stopped at **9 decisions**;
- exactly five later frame/context pairs were replayed;
- driver learning and external reinforcement were suppressed;
- paired branches started from the same pre-event checkpoint;
- reward-pulse efficacy effect remained confined to the reward compartment;
- transient neural state was cleared before recall;
- synaptic memory survived the reset;
- recall plasticity was frozen;
- recall delivered no external reinforcement.

## Synaptic result

Across all four replicates:

- mean immediate reward-compartment paired L1 difference:
  **4.600586304257245**
- mean paired L1 difference after five reinforcement-free replay decisions:
  **7.02223958687067**
- delayed/immediate L1 ratio:
  **1.526379274827**
- off-target paired L1 difference:
  **0**

The paired reward-compartment difference therefore did not decay over this
five-decision assay. It increased.

This is evidence about the current engineered plasticity mechanism, not an
independent biological memory-duration claim.

## State-cleared cue recall

After the five-decision delay, both branches had transient neural state cleared
with `brain.reset(keep_memory=True)`, wrapper visual history cleared, and
plasticity frozen.

The exact original reward cue was then replayed with no reinforcement.

Across **4/4 replicates**:

- action divergence: **0**
- DNp20 right-minus-left rate delta: **0 Hz**
- DNpe017 gate-spike delta: **0**
- KC-spike delta: **0**
- total-spike delta: **0**

Both branches produced the same decoded action in every replicate.

## Interpretation

The current model now shows two separable facts:

1. a true reward pulse leaves a compartment-local synaptic difference that
   persists, and in this assay increases, during five later no-reinforcement
   decisions;
2. after transient-state clearing, that synaptic difference produces **no
   detected difference in the current recall neural/motor readout** for the
   identical cue.

Therefore the next bottleneck is not whether a memory-like synaptic difference
exists. It is **memory expression / readout**.

A behavioral confirmatory study is not justified from this run alone.

## Next preregistered question

Audit the expression path without changing learning parameters:

1. identify which KC→MBON07 edges carry the paired reward-memory difference;
2. measure whether their presynaptic KCs are active during the state-cleared
   recall cue;
3. measure paired MBON07 response directly;
4. if MBON07 differs, trace whether the difference propagates to the current
   DNp20/DNpe017 decoder;
5. if changed-edge KCs are not cue-active, distinguish storage from cue-indexing
   failure before any behavioral confirmatory study.

## Claim state

All remain false:

- `learning_validated`
- `reward_memory_persistence_causal`
- `cue_conditioned_behavior_effect_causal`
- `reinforcement_mechanism_validated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
