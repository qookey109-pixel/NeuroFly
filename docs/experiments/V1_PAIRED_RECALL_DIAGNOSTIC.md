# V1 Paired Recall Diagnostic

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Question

The previous compartment diagnostic established an implementation-level fact:
under the frozen rule, one true task reinforcement pulse changes only the
preselected KC→MBON memory compartment.

The next question is whether that paired compartment difference survives
subsequent reinforcement-free neural processing and changes the later response
to the same sensory cue.

## Design

Four fresh trajectory seeds are frozen:

- RCL1 / 2459
- RCL2 / 2467
- RCL3 / 2473
- RCL4 / 2477

For every reinforced event with at least eight later recorded frames:

1. rebuild the exact pre-event state using no external reinforcement history;
2. fork two identical branches;
3. present the event cue with either no pulse or the frozen true task pulse;
4. replay exactly eight later recorded frames/contexts to both branches;
5. force reinforcement=`none` throughout the delay;
6. replay the exact original event frame/context once more with no reinforcement;
7. compare persistent compartment memory and recall neural/action response.

No branch controls the world during replay. Both branches receive identical
recorded sensory inputs, so branch divergence cannot change the later cue
sequence.

## Fixed delay

The delay is eight MaleCNS decisions, each using the frozen 50 ms neural window.

This is an engineered replay interval, not a biological real-time memory claim.

## Primary descriptive endpoints

- immediate target-compartment L1 difference;
- delayed target-compartment L1 difference;
- delayed/immediate target-L1 persistence ratio;
- delayed target mean signed efficacy difference;
- recall action-divergence fraction;
- recall left-right decoder difference delta;
- recall gate-spike delta;
- recall total-spike delta.

Reward and aversive events are also reported separately when present.

## No tuning

The study does not modify:

- eta;
- pulse current or duration;
- DAN baseline;
- trace recentering;
- decoder threshold;
- memory bounds;
- sensory adapters;
- compartment definitions;
- reward thresholds.

There is no directional PASS threshold. All eligible reinforced events are
included; events are not selected by their observed effect.

## Claim boundary

Even if persistent memory or recall-response differences are observed, all of
these remain false:

- `learning_validated`
- `paired_recall_effect_causal`
- `cue_conditioned_behavior_validated`
- `reinforcement_mechanism_validated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

This study can justify or reject the next mechanistic step. It cannot substitute
for a later preregistered behavioral confirmatory study.
