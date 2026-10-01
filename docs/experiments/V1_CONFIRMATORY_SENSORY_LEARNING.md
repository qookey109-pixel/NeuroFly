# V1 — Confirmatory Sensory-Only Learning Study

## Purpose

The first four-arm learning-control run produced an exploratory performance
signal, but it is not eligible as confirmatory NeuroFly v1 learning evidence.

Two methodological issues were identified after that run:

1. it used the legacy GoalMazeSession path, whose brain context can include
   world-side simulator metadata;
2. it used a 3600-second world clock while agent decisions suppressed direct
   enemy movement, so short held-out runs did not establish independent
   seed-driven predator trajectories.

This protocol fixes both issues before confirmatory data are observed.

## Architecture boundary

Every normal-sensory confirmatory arm uses:

GoalMazeEnvironment
→ MazeChaseAdapter
→ EnvironmentSession
→ ControlledBrain
→ real MaleCNS

MazeChaseAdapter retinalizes the top-down simulator render and strips
world-truth olfactory source geometry before neural handoff.

The confirmatory runner audits the exact context that reaches MaleCNS on every
decision.

Normal sensory decisions must pass the shared privileged-state firewall.

The sensory-off arm must deliver an empty neural context.

## Seeded environment dynamics

The confirmatory path uses MazeChaseAdapter.apply_action(), which calls
GoalMazeEnvironment.step().

GoalMazeEnvironment.step() advances predator motion synchronously on every
action. Therefore the preregistered RNG seed directly influences realized enemy
trajectories rather than waiting on a separate wall-clock thread.

## Fixed sample size

Exactly 10 paired replicates are preregistered.

There is no optional stopping and no data-dependent extension.

Each replicate uses:

- one unique training seed;
- two unique held-out evaluation seeds;
- all four study arms;
- the same immutable baseline MaleCNS checkpoint.

Training:

- 60 decisions per arm.

Held-out evaluation:

- 40 decisions per seed;
- learning disabled;
- weights frozen;
- reinforcement delivered to brain suppressed to none;
- normal sensory input restored;
- fresh brain restore for every held-out seed;
- fresh environment for every held-out seed.

## Fixed seeds

| Replicate | Training | Held-out evaluation |
| ---: | ---: | --- |
| 1 | 211 | 811, 821 |
| 2 | 223 | 823, 827 |
| 3 | 227 | 829, 839 |
| 4 | 229 | 853, 857 |
| 5 | 233 | 859, 863 |
| 6 | 239 | 877, 881 |
| 7 | 241 | 883, 887 |
| 8 | 251 | 907, 911 |
| 9 | 257 | 919, 929 |
| 10 | 263 | 937, 941 |

These values are frozen before confirmatory execution.

## Primary endpoint

The only confirmatory primary endpoint is:

mean held-out total reward

for each arm within each replicate.

Food, clears, deaths and HOLD fraction remain secondary descriptive metrics and
cannot rescue a failed primary endpoint.

## Pairwise controls

learning_true is paired against:

- frozen_true;
- learning_scrambled;
- learning_sensory_off.

A paired reward difference of exactly zero does not count as a positive
replicate.

## Confirmatory decision rule

Every one of the three comparisons must satisfy all of the following:

1. learning_true has higher held-out reward in at least 9 of 10 replicates;
2. median paired reward difference is at least +1.0;
3. the exact one-sided sign-test p-value passes Holm-Bonferroni family-wise
   correction at alpha = 0.05 across all three comparisons.

With n=10:

- 9/10 positive gives exact one-sided p = 11/1024 ≈ 0.010742;
- 8/10 positive gives p = 56/1024 ≈ 0.054688 and cannot pass.

The protocol therefore cannot be relaxed after observing confirmatory results.

## Interpretation

If execution is valid and all three comparisons pass, the receipt may set:

learning_validated = true

with the narrow scope:

this fixed MaleCNS checkpoint on Goal Maze under preregistered environment
randomization.

Even a confirmatory PASS does not set:

- causal_learning_claim_authorized;
- generalization_validated;
- behavioral_promotion_authorized.

Those remain false because this study covers one task family, one baseline
checkpoint and engineered sensory proxies.

## Failure semantics

A scientifically negative result is not a CI failure.

If all execution-integrity gates pass but the confirmatory decision rule fails,
the receipt status is:

CONFIRMATORY_FAIL

and learning_validated remains false.

If an execution-integrity gate fails, the receipt status is:

INVALID_EXECUTION

and the workflow fails closed.

Technical failures do not remove or replace a replicate after outcomes are
observed.

## Production isolation

The workflow restores the production brain only as a read-only source.

All replicate checkpoints live under the isolated study directory.

No confirmatory arm is saved back into production cache and no behavioral
promotion is performed automatically.
