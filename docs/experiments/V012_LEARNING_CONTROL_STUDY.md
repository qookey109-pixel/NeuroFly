# V0.12 — Real MaleCNS Learning Control Study

## Purpose

NeuroFly can already run MaleCNS with plasticity enabled, receive engineered
reinforcement and persist neural state. Those facts alone do not prove that an
observed behavioral change is caused by learning.

This study adds the missing controls.

## Preregistered arms

Every arm starts from an identical copy of the same production MaleCNS brain
checkpoint and the same training maze seed.

1. learning_true
   - learning enabled
   - normal sensory input
   - task-contingent reinforcement

2. frozen_true
   - learning disabled and weights frozen
   - normal sensory input
   - task-contingent reinforcement

3. learning_scrambled
   - learning enabled
   - normal sensory input
   - deterministic synthetic reinforcement independent of task outcome

4. learning_sensory_off
   - learning enabled
   - visual input blanked
   - context stripped, including olfaction and game geometry
   - task-contingent reinforcement remains available

The scrambled schedule is fixed by code before results are observed. It is a
specificity control, not an attempt to reproduce the empirical reward frequency
of the treatment arm.

## Held-out evaluation

Training and evaluation are separated.

After each arm finishes training, its checkpoint is reloaded for each held-out
maze seed:

- 701
- 709
- 719

During evaluation:

- learning is disabled;
- weights are frozen;
- reinforcement delivered to the brain is always none;
- normal visual and olfactory sensory input is restored for every arm.

An evaluation difference therefore cannot be created by additional online
plasticity or by different evaluation reinforcement.

## Primary descriptive metrics

The first study reports:

- mean total reward
- mean total clears
- mean total food
- mean total deaths
- mean HOLD fraction

It also records action counts, neural activity verification, checkpoint hashes
and delivered reinforcement counts.

The receipt reports learning_true minus each control for every primary metric.

## No automatic verdict

Version 0.1 intentionally defines no winner, no score, no p-value threshold and
no automatic learning verdict.

A completed execution remains:

HUMAN_REVIEW_REQUIRED

The following remain false:

- learning_validated
- generalization_validated
- causal_learning_claim_authorized
- behavioral_promotion_authorized

This prevents one exploratory run from becoming an accidental scientific claim.

## Isolation

The manual workflow restores the current production checkpoint as a read-only
source and copies only the brain checkpoint into an isolated study directory.

The study verifies that:

- every arm begins from the same source SHA-256;
- the source checkpoint SHA-256 is unchanged after the study;
- each arm has its own checkpoint path.

The workflow does not:

- overwrite the production brain;
- save any study arm back to production cache;
- publish to main;
- dispatch continuous training;
- promote a model.

Only compact preflight and study receipt evidence are uploaded.

## Interpretation boundary

If execution succeeds, the result means only that a controlled real-MaleCNS
learning comparison is available for review.

A later confirmatory study can preregister independent replicates, a primary
endpoint, effect direction, uncertainty/statistical method, minimum practical
effect and stopping rule before confirmatory results are observed.
