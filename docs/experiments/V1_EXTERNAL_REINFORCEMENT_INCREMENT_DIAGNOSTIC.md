# V1 External Reinforcement Increment Diagnostic

## Question

After DAN trace recentering removed the large coordinate-mismatch drift, what
plasticity increment is attributable to the task's external reinforcement
signal itself?

## Isolation design

For each fresh seed, one real MaleCNS trajectory runs with:

- normal biological sensory adapters;
- live neural weights frozen;
- live external reinforcement suppressed;
- live zero DAN baseline;
- decision-synchronous world motion.

The task outcome still generates the same delayed categorical reinforcement
schedule that a normal GoalMazeSession would deliver on the next decision.

Every 10 ms bin is copied to two isolated, calibrated-and-recentered shadow
plasticity states:

1. `endogenous_only`: endogenous DAN residual only.
2. `true_external`: same endogenous trajectory plus the recorded task
   reinforcement increment during the first 20 ms of the corresponding next
   decision.

Because the live network is frozen and receives no external pulse, both shadows
share the same KC/endogenous-DAN trajectory.

## Important limitation

The shadow external increment is injected at the plasticity-rule DAN-rate
input. It does **not** replay the nonlinear LIF network response that a real
20 ms DAN current pulse would produce. Therefore this is a rule-input
increment diagnostic, not a full-network causal pulse intervention.

## Endpoints

- number of externally reinforced decisions;
- true-minus-endogenous early efficacy delta;
- true-minus-endogenous final efficacy delta;
- reward-compartment net-drive increment;
- aversive-compartment net-drive increment;
- proof that live frozen memory did not change.

No automatic scientific PASS threshold is defined.

## Governance

This diagnostic cannot by itself validate learning, confirm a temporal-credit
defect, authorize replacement confirmatory testing, or promote behavior.
