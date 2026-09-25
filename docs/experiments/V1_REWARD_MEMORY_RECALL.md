# V1 Reward Memory Recall Diagnostic

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Question

Run 1 of the compartment plasticity diagnostic established that, under the
frozen model, reward-pulse edge differences are localized entirely to the
predefined reward memory compartment. It did not test whether that synaptic
difference has a later functional consequence.

This study asks:

> After one natural reward event, does the compartment-local synaptic
> difference produced by true external reinforcement survive five identical
> no-reinforcement replay decisions and, after clearing transient neural state,
> change the response to the identical reward cue?

## Why reward only

The prior diagnostic observed 15 reward events but only one aversive event.
The aversive sample is therefore not used to motivate a balanced recall claim.

This study deliberately narrows to reward memory. Aversive recall requires its
own adequately sampled preregistered study.

## Frozen design

Four fresh trajectory seeds:

- R1: 2609
- R2: 2617
- R3: 2621
- R4: 2633

For each frozen trajectory, the study chooses the **first natural reward event
with at least five subsequent recorded decisions**. This rule is fixed before
execution; no event is selected by observed neural or memory effect.

For each replicate:

1. reconstruct the exact pre-event checkpoint with external reinforcement
   suppressed in prior history;
2. branch from the same checkpoint:
   - no pulse;
   - true reward pulse;
3. replay the next five exact sensory frame/context pairs to both branches with
   external reinforcement suppressed;
4. measure reward-compartment paired efficacy difference before and after the
   replay window;
5. clear transient neural state with `brain.reset(keep_memory=True)`;
6. clear the wrapper's visual-history state;
7. freeze plasticity;
8. present the exact original reward-event frame/context to both branches with
   no reinforcement;
9. compare neural readout and decoded action.

## Primary descriptive endpoints

- reward-compartment L1 difference immediately after the event;
- reward-compartment L1 difference after five replay decisions;
- L1 retention ratio;
- recall action divergence;
- recall DNp20 right-minus-left rate delta;
- recall DNpe017 gate-spike delta;
- recall total-spike delta;
- recall KC-spike delta.

No behavioral PASS threshold is defined.

## Isolation boundary

The state-clearing recall is deliberately stronger than simply continuing the
live game. It removes transient membrane, queue, trace-rate and visual-history
state while preserving the branch's synaptic memory.

Recall plasticity is frozen, so the cue cannot create a new memory difference
during the measurement itself.

This is an engineered mechanistic assay, not a claim that biological flies
undergo a literal reset.

## Locked claims

Regardless of result, all remain false:

- `learning_validated`
- `reward_memory_persistence_causal`
- `cue_conditioned_behavior_effect_causal`
- `reinforcement_mechanism_validated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
