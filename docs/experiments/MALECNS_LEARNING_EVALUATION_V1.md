# MaleCNS Learning Evaluation V1

Status: **protocol specification only — not yet executed**  
Protocol ID: `neurofly-learning-evaluation-v1`

## Purpose

NeuroFly's live curriculum can show movement, food acquisition, maze coverage, neural activity, plasticity state, and engineered reward exposure. None of those observations alone establish that the MaleCNS connectome simulation learned a useful navigation policy.

This protocol defines the minimum controlled evidence required before NeuroFly may describe a behavioral change as learning rather than movement, anti-stall assistance, sensory bias, reward exposure, or chance.

## Claims boundary

The following must remain separate in every report:

- **raw MaleCNS action**: action decoded from simulated connectome activity;
- **applied environment action**: action actually executed after any transparent engineered override;
- **behavioral outcome**: food, coverage, capture, clear, time/decisions to clear;
- **plasticity evidence**: persistent checkpoint / memory state change;
- **learning claim**: allowed only after controlled comparisons below.

Anti-stall overrides are locomotion safety assistance. Improvement caused only by a higher override rate is not evidence that the MaleCNS learned navigation.

## Required experimental arms

All arms use the same pinned Stonkfly revision, same decoder version, same canonical maze family, same decision budget, and predeclared seeds.

| Arm | Plasticity | Reward | Olfaction | Purpose |
| --- | --- | --- | --- | --- |
| A — candidate | enabled | real | on | candidate learned behavior |
| B — frozen-plasticity control | frozen | real | on | separates persistent learning from immediate sensory response |
| C — randomized-reward control | enabled | randomized / sham | on | tests whether reward contingency matters |
| D — odor-off control | enabled | real | off | tests whether engineered olfactory information contributes |
| E — held-out validation | frozen during validation | no learning update during validation | on | tests whether behavior transfers to an unseen validation maze without adapting on it |

A future implementation may add more controls, but it must not remove these arms without a new protocol version.

## Primary metrics

Report every arm, including zero-result arms. Do not cherry-pick successful episodes.

1. food acquisitions per 100 neural decisions;
2. unique-cell coverage ratio;
3. clear count and clear rate;
4. decisions to clear and active seconds to clear;
5. capture/death count and rate;
6. raw action histogram;
7. applied action histogram;
8. engineered override rate and reasons;
9. bilateral food-cue side versus **raw** MaleCNS action distribution;
10. raw directional-turn alignment when the raw action is `TURN_LEFT` or `TURN_RIGHT`;
11. persistent checkpoint / memory identity before and after training.

## Evaluation rules

- Raw and applied actions must never be merged into one metric.
- A run with zero clears is reported as zero clears.
- Missing values are reported as unavailable, never converted to zero unless zero is the actual measured value.
- Validation data must not update the training checkpoint.
- Held-out validation mazes must be fixed before seeing candidate validation results.
- Any decoder, reward, sensory, anti-stall, maze, or threshold change creates a new experimental condition and must be identified explicitly.
- Results from different protocol versions must not be pooled as if they were the same experiment.

## Minimum evidence for a learning claim

A learning claim requires all of the following:

1. the candidate checkpoint is persistent and provenance-valid;
2. Arm A improves on predeclared primary behavioral metrics relative to Arm B;
3. the improvement is not reproduced by randomized/sham reward in Arm C;
4. olfaction-dependent claims are supported by the Arm D contrast;
5. the improvement remains observable on Arm E while learning is frozen;
6. override-rate changes do not explain the apparent improvement;
7. all arms and failures are reported.

No single threshold is hard-coded here because effect-size and replication thresholds must be declared before the first controlled run. The first execution of this protocol must add a versioned run manifest containing those thresholds and seeds before any results are inspected.

## What current live training can establish

Current live training can establish that:

- verified MaleCNS neural activity drove decoded raw actions;
- engineered sensory cues reached the configured neural targets;
- reward / aversive events and plasticity mechanisms were exercised;
- persistent checkpoints accumulated state across bounded runs;
- observable behavior occurred in the environment.

Until the controlled arms above are executed, current live training **does not establish** learned navigation, general intelligence, biological intent, subjective experience, or autonomous understanding of the maze.
