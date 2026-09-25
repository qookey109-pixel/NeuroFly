# V1 event-local compartment plasticity diagnostic

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## New question

The previous learning-mechanism branch closed after showing that the existing
task pulse produces a negative immediate **global mean efficacy** shift relative
to an identical no-pulse branch.

That result does not answer whether the pulse changes the anatomically intended
memory compartment in a structured way.

This study therefore asks a different, preregistered question:

> Does a true task reinforcement pulse produce edge-level efficacy
> redistribution concentrated in the anatomically intended KC-to-MBON memory
> compartment relative to an identical no-pulse branch?

## Why this is not post-hoc tuning

Nothing in the learning rule is changed:

- eta unchanged;
- decoder thresholds unchanged;
- pulse current unchanged at 20.0;
- pulse duration unchanged at 20 ms;
- reward thresholds unchanged;
- calibrated DAN baseline unchanged;
- trace recentering unchanged.

The only change is measurement resolution: from global mean efficacy to the
already-fixed KC-to-MBON edge compartments.

## Frozen compartments

The pinned Stonkfly circuit defines two memory output compartments:

- PAM11-driven reward compartment → KC-to-MBON07 edges;
- PPL101-driven aversive compartment → KC-to-MBON11 edges.

The diagnostic derives the edge masks only from the frozen circuit gain matrix.
Edges are never selected based on the observed result.

For reward events the target is the MBON07 compartment. For aversive events the
target is the MBON11 compartment.

## Paired event design

Four fresh trajectory seeds are preregistered:

- C1: 2309
- C2: 2311
- C3: 2333
- C4: 2339

For every naturally occurring task reward/aversive event:

1. rebuild the exact pre-event state using no external reinforcement history;
2. save one immutable pre-event checkpoint;
3. branch once with no pulse;
4. branch once with the true task pulse;
5. compare the complete plastic-edge efficacy vector;
6. partition the paired difference using the frozen reward/aversive masks.

The driver trajectory remains frozen and decision-synchronous.

## Primary descriptive endpoints

Separately for reward and aversive events:

- target-compartment L1 fraction of the paired edge difference;
- target mean signed efficacy difference;
- target negative-edge fraction;
- target positive-edge fraction;
- target versus off-target mean absolute change;
- maximum off-target absolute edge change;
- fraction of events where target L1 exceeds off-target L1.

The study also records immediate action divergence and exact edge/mask digests.

No directional PASS threshold is defined before execution. This experiment is
mechanistic characterization, not a confirmatory learning test.

## Integrity checks

Execution is invalid unless:

- all four fresh trajectories complete;
- every replicate contains at least one reinforced event;
- both reward and aversive events occur somewhere in the study;
- every branch starts with identical edge efficacy state;
- plastic edge topology and compartment masks stay identical across all pairs;
- the checkpoint's efficacy fraction agrees with Stonkfly `memory_w`;
- no-pulse branches deliver zero stimulus;
- true branches deliver exactly 20 ms;
- the source production checkpoint remains unchanged.

## Claim boundary

Regardless of the observed direction, this study keeps all of these false:

- `learning_validated`
- `compartment_specificity_causal`
- `reinforcement_mechanism_validated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

A useful result may justify a separately reviewed next question. It cannot by
itself promote behavioral learning.
