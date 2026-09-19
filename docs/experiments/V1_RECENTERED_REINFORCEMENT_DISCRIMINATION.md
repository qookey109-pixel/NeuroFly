# V1 Recentered Reinforcement Discrimination

## Purpose

Counterfactual Rule Replay Run 35417521260 removed neural-trajectory feedback
and showed that the large positive plastic drift is dominated by a DAN trace
coordinate mismatch. Recentered replay reduced the mean final drift from about
+0.1444 to +0.00023 on the same frozen trajectories.

The next question is practical: after applying the coordinate-consistent DAN
trace state, can real task reinforcement be distinguished from residual
unreinforced plasticity and synthetic scrambled reinforcement?

This is exploratory. It is not a replacement confirmatory study.

## Common state

Every arm:

- starts from the same production checkpoint copy;
- applies the frozen 17-cell task-conditioned DAN baseline;
- transforms the persisted DAN trace exactly once:
  `rate_dan := rate_dan - dan_baseline_hz`;
- uses normal sensory input;
- uses decision-synchronous seeded world updates;
- trains for 60 decisions;
- is evaluated frozen for 20 decisions on each of two held-out seeds.

No eta, decoder, reward-strength, or baseline tuning is allowed.

## Arms

- `learning_true_recentered`
- `learning_none_recentered`
- `learning_scrambled_recentered`
- `frozen_true_recentered`

The true arm receives the task's actual delayed reinforcement. The none arm
suppresses external reinforcement. The scrambled arm receives deterministic
synthetic reinforcement independent of task outcome. The frozen arm receives
the true task signal with plastic weights frozen.

## Descriptive endpoints

- final mean-efficacy drift;
- memory changes on externally unreinforced decisions;
- memory changes on externally reinforced decisions;
- frozen held-out mean reward;
- frozen held-out HOLD fraction.

The main descriptive contrasts are:

- true minus none;
- true minus scrambled;
- true minus frozen.

No automatic PASS threshold is defined.

## Interpretation boundary

A clean separation of true from none and scrambled would support proceeding to
a stronger preregistered remediation study. It would not by itself validate
learning, authorize production promotion, or authorize replacement
confirmatory testing.

The following remain false:

- `learning_validated`
- `true_reinforcement_discriminated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
- `production_checkpoint_mutated`
