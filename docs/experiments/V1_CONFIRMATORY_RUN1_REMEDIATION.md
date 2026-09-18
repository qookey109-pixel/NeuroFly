# V1 Confirmatory Run #1 — Negative Result and Seed-Effectiveness Remediation

## Authority anchors

The first preregistered confirmatory learning execution is preserved as an
observed historical result.

- workflow: NeuroFly Confirmatory Learning Study
- run id: 35323343414
- run number: 1
- checkout: 65f6d5aa7b2df186f03802b3214cf65bb77f7afd
- workflow conclusion: SUCCESS
- artifact id: 10538298687
- artifact digest:
  sha256:a85d16c080c5c9bbf6a39a7ac8c07419c7a3d9cbc89dca5baa699494f0228d52
- receipt:
  610b28444c8d3481397b6a56500e9f4cd17f66e059ce4c3c9cb73ba9fe636b8c

The compact immutable repository freeze is:

`data/confirmatory_learning_run1_freeze_v01.json`

## Raw preregistered result

The v0.1 workflow executed successfully under the gates that existed before
execution and returned:

`CONFIRMATORY_FAIL`

Observed co-primary results:

- learning_true - frozen_true
  - mean reward effect: -4.0
  - positive replicates: 0/8
  - preregistered requirement: mean >= +1.0 and at least 7/8 positive
- learning_true - learning_scrambled
  - mean reward effect: -0.875
  - positive replicates: 0/8
  - preregistered requirement: mean >= +1.0 and at least 7/8 positive

The supportive learning_true - learning_sensory_off comparison had mean reward
effect 0.0 and 0/8 positive replicates.

Therefore the historical receipt correctly left these claims closed:

- learning_validated = false
- within_task_heldout_generalization_supported = false
- causal_learning_claim_authorized = false
- behavioral_promotion_authorized = false

This negative result is not rewritten or converted into a pass.

## Post-run diagnostic finding

After the result was observed, a separate exploratory diagnostic found that the
v0.1 seed design did not materially perturb the study environment during the
bounded 60/20-decision windows.

The relevant interaction was:

1. the study created GoalMazeSession with `world_tick_seconds=3600.0`;
2. GoalMazeSession applied agent decisions through
   `agent_step(..., move_enemies=False)`;
3. the GoalMazeEnvironment seed drives the RNG used by enemy movement;
4. the 3600-second world clock never fired during the bounded study;
5. therefore the seeded enemy-movement RNG was not consumed.

The intended training and held-out seed differences were consequently inert for
the deterministic study arms.

The full receipt showed this directly across all eight nominal replicates:

- learning_true:
  - one unique training metric signature;
  - one unique post-training checkpoint SHA;
  - one unique evaluation aggregate signature;
- frozen_true:
  - one unique training metric signature;
  - one unique post-training checkpoint SHA;
  - one unique evaluation aggregate signature;
- learning_sensory_off:
  - one unique training metric signature;
  - one unique post-training checkpoint SHA;
  - one unique evaluation aggregate signature.

learning_scrambled varied because its synthetic reinforcement stream has its own
arm-specific scramble seed. That variation does not demonstrate that the Maze
training or held-out seeds were effective.

## Interpretation

Two statements must be kept separate.

First, the original receipt's `execution_valid=true` remains historically
accurate for the preregistered v0.1 contract gates that existed at execution.

Second, the run does not support the intended independent-replicate or held-out
seed generalization interpretation because v0.1 had no gate proving that seeds
materially changed the environment.

Accordingly:

- the negative outcome remains frozen;
- the original thresholds are not relaxed;
- Run #1 is not rerun under modified code and relabeled as the same study;
- replicate_independence_supported = false for the post-run diagnostic;
- held_out_seed_effectiveness_supported = false for the post-run diagnostic.

## Remediation design

A new exploratory-only v0.2 path is introduced without changing v0.1 defaults.

GoalMazeSession gains an opt-in `decision_synchronous_world` mode. When
enabled, enemy movement occurs exactly once per agent decision. This keeps the
study deterministic while ensuring the environment consumes its seeded RNG.

The v0.1 learning helpers retain:

`decision_synchronous_world=False`

as their default so the historical procedure remains reproducible.

The exploratory remediation is locked in:

`data/learning_remediation_study_v01.json`

It uses fresh seeds, four matched exploratory replicates, the same four control
arms, 60 training decisions and 20 frozen evaluation decisions per held-out
seed.

Before any MaleCNS result is accepted, every configured seed is independently
run through a fixed HOLD-action environment probe. Every configured seed must
produce a unique trace digest.

If seed-effectiveness fails, the remediation receipt is:

`INVALID_EXECUTION`

and no learning interpretation is permitted.

## Claim boundary

The remediation workflow is exploratory only.

Even if its descriptive effects are positive:

- learning_validated remains false;
- within_task_heldout_generalization_supported remains false;
- causal_learning_claim_authorized remains false;
- broad_generalization_validated remains false;
- behavioral_promotion_authorized remains false;
- replacement_confirmatory_authorized remains false.

A replacement confirmatory study requires a new preregistration after the
exploratory remediation evidence is reviewed.
