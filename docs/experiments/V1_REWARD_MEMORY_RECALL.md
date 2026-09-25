# V1 Reward Memory Recall Diagnostic

Status: **V0.1 INVALID / V0.2 PREREGISTERED EXPLORATORY EXECUTION**

## Origin

The merged compartment-plasticity study established that the immediate paired
reward-pulse efficacy difference is confined to the predefined reward memory
compartment. It did not establish persistence or later cue-conditioned
function.

## V0.1 invalid freeze

V0.1 used four fresh seeds and a fixed 60-decision acquisition window.

It is **not scientific evidence**.

- run `36091139488` reached the final receipt stage but failed because runtime
  NumPy arrays were included in the JSON evidence object; no accepted receipt
  exists;
- after fixing serialization, run `36093996850` failed before recall endpoints
  because at least one preregistered seed had no natural reward event with five
  later decisions remaining inside the fixed 60-decision window.

The second failure is a design-feasibility failure, not a negative memory
result. Seeds may not be replaced after observing this failure.

Machine-readable freeze:

`data/reward_memory_recall_v01_invalid_freeze.json`

## V0.2 question

> After the first natural reward event, does the compartment-local synaptic
> difference produced by true external reinforcement survive five identical
> no-reinforcement replay decisions and, after clearing transient neural state,
> change the response to the identical reward cue?

## V0.2 acquisition rule

Four new seeds are frozen before execution:

- R2-1 / 2711
- R2-2 / 2713
- R2-3 / 2719
- R2-4 / 2729

For each replicate, the frozen driver starts at decision zero and records until:

1. the **first natural reward** is observed; then
2. exactly **five subsequent decisions** are recorded.

Maximum acquisition length is **300 decisions**.

If a seed has no reward within that maximum, the replicate and study are
invalid. The seed is not replaced.

This changes only event acquisition feasibility. It does not tune an observed
memory or neural effect.

## Paired state-cleared recall

For the first natural reward event in each valid acquisition:

1. reconstruct the exact pre-event checkpoint with external reinforcement
   suppressed in prior history;
2. branch from that identical checkpoint:
   - no pulse;
   - true reward pulse;
3. replay the next five exact frame/context pairs to both branches with external
   reinforcement suppressed;
4. measure the paired reward-compartment efficacy difference immediately after
   the event and after the five-decision delay;
5. call `brain.reset(keep_memory=True)`;
6. clear wrapper visual-history state;
7. freeze plasticity;
8. replay the exact original reward-event frame/context with no reinforcement;
9. compare neural readout and decoded action.

## Primary descriptive endpoints

- post-event reward-compartment L1 difference;
- post-delay reward-compartment L1 difference;
- L1 retention ratio;
- recall action divergence;
- recall DNp20 right-minus-left rate delta;
- recall DNpe017 gate-spike delta;
- recall total-spike delta;
- recall KC-spike delta.

No behavioral PASS threshold is defined.

## Isolation boundary

The reset removes transient neural state while preserving the branch's synaptic
memory. Recall plasticity is frozen, so recall cannot create a new branch
difference.

This is an engineered mechanistic assay, not a claim that a biological fly
undergoes a literal reset.

## Locked claims

Regardless of result, all remain false:

- `learning_validated`
- `reward_memory_persistence_causal`
- `cue_conditioned_behavior_effect_causal`
- `reinforcement_mechanism_validated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
