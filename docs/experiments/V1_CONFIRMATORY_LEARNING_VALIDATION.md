# V1 — Confirmatory Learning Validation Study

## Purpose

The first real-MaleCNS four-arm learning-control study produced a promising
exploratory signal, but it intentionally did not authorize a learning claim.

This study is the next stage: the decision rule is fixed before confirmatory
results are observed.

The exploratory evidence anchor is:

- run 35315263154
- receipt d14be40f2dc3f589548e9e36e453090a2db0605124b5b690d8779b1ff1d958bc

The exploratory result may motivate the design, but it is not counted as one of
the confirmatory replicates.

## Fixed training and evaluation dose

The confirmatory study keeps the same dose used in the exploratory study:

- 60 training decisions per arm;
- 20 frozen evaluation decisions per held-out seed.

Changing the dose after observing the exploratory effect would create a new
study question, so the workflow exposes no inputs that can alter these values.

## Eight matched independent replicates

Each replicate contains the same four arms:

1. learning_true
2. frozen_true
3. learning_scrambled
4. learning_sensory_off

Within a replicate all four arms begin from the same production-brain SHA and
use the same training environment seed.

Across replicates, training seeds are distinct.

Every replicate also has three unique held-out evaluation seeds. No
confirmatory seed reuses the exploratory training seed 109 or exploratory
held-out seeds 701, 709 and 719.

The exact replicate seed table is frozen in
data/confirmatory_learning_study_v01.json.

## Frozen evaluation

Every trained arm is evaluated with:

- learning disabled;
- weights frozen;
- reinforcement delivered to the brain set to none;
- normal sensory input restored.

The confirmatory endpoint therefore measures persisted post-training
differences rather than additional evaluation-time plasticity.

## Primary endpoint

The single primary metric is:

mean_total_reward

computed over the three held-out seeds inside each replicate.

## Co-primary contrasts

Two contrasts must both pass:

- learning_true minus frozen_true
- learning_true minus learning_scrambled

The first tests whether plasticity matters.

The second tests whether task-contingent reinforcement matters rather than
plasticity under an unrelated reinforcement schedule.

## Confirmatory decision rule

For each co-primary contrast:

- mean reward effect across eight replicates must be at least +1.0;
- at least 7 of 8 replicate reward effects must be strictly positive.

Both co-primary contrasts must pass.

The +1.0 practical threshold was chosen after the exploratory study but before
confirmatory execution. In the current Maze reward scale it is approximately
one additional food-reward unit, so the criterion requires more than an
arbitrarily small numerical advantage.

The 7-of-8 requirement is a replication-consistency rule. This version does not
use a post-hoc p-value threshold.

## Sensory-dependence support

The learning_true minus learning_sensory_off contrast is supportive rather than
co-primary.

It requires:

- positive mean reward effect;
- at least 5 of 8 positive replicate effects.

Failure of this supportive contrast does not change the primary learning
verdict, but it prevents authorization of the stronger causal-learning claim.

## Claim policy

If both co-primary contrasts pass:

learning_validated = true

and:

within_task_heldout_generalization_supported = true

This generalization statement is deliberately narrow: it refers only to new
Maze seeds from the same task family.

The broad flag remains:

generalization_validated = false

If the co-primary rule and sensory-dependence support both pass:

causal_learning_claim_authorized = true

Even then:

behavioral_promotion_authorized = false

Promotion into a production curriculum or release policy remains a separate
governance action.

## Negative results are valid results

The workflow must succeed operationally even when the confirmatory rule fails.

A scientifically valid negative execution is recorded as:

CONFIRMATORY_FAIL

A workflow failure is reserved for invalid execution, broken evidence gates,
source mutation or contract drift.

This prevents CI status from being confused with the biological result.

## Isolation

The production brain is restored only as a read-only source and copied into an
isolated study baseline.

Every arm receives a separate checkpoint path.

The production source SHA must be identical before and after the experiment.

No confirmatory arm is saved back into the production cache.

## Execution authority

Normal pull-request CI validates:

- the preregistration contract;
- the locked decision rule;
- fail-closed evaluation;
- workflow immutability.

A real confirmatory conclusion requires the dedicated workflow to execute from
an authority branch after this machinery is integrated.
