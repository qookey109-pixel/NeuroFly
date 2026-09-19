# V1 Full-Network Reinforcement Pulse Replay

Status: **EXPLORATORY INTERVENTION ONLY**

This study follows External Reinforcement Increment Run #2
(`35426688269`, receipt
`d0f685da13ebcfc805fb954bfd4567d9d41b86932649d31635f5d6c436f63a2f`).

## Why this study exists

Run #2 replayed the plasticity rule on one frozen neural trajectory and inserted an
equivalent compact DAN-rate increment. It was execution-valid and produced a
negative true-minus-endogenous final mean efficacy contrast in all four
replicates, but that intervention bypassed Stonkfly's LIF response to the actual
reinforcement current.

This study removes that limitation.

## Paired design

For each fresh trajectory seed:

1. A frozen, no-external-reinforcement MaleCNS driver controls the synchronous
   maze for 60 decisions.
2. The exact frame, sensory context and *incoming true task reinforcement*
   presented at every decision are recorded.
3. Two independent learning-enabled MaleCNS brains start from the same production
   checkpoint.
4. Both receive the identical recorded frame/context sequence.
5. `endogenous_only` receives `reinforcement="none"`.
6. `true_external` receives the recorded task reinforcement through
   `MaleCNSBrain.decide()`, so the existing 20 ms / 20.0 reinforcement
   stimulation is processed by the full LIF network before the plasticity rule.
7. Replay decoder actions are measured but never fed back into the environment.
   Therefore both conditions retain an identical sensory/world trajectory even
   when neural outputs diverge.

Fresh seeds: `2141, 2143, 2153, 2161`.

Both replay conditions use the calibrated DAN baseline and the already-defined
trace recentering transform. No eta, decoder threshold, pulse size, reward
threshold, or production checkpoint is tuned.

## Primary descriptive endpoints

- number of recorded external-reinforcement decisions;
- true-minus-endogenous final mean efficacy delta;
- reward-DAN spike increment on reward events;
- aversive-DAN spike increment on aversive events;
- paired replay action-divergence fraction;
- frozen trajectory-driver memory delta.

## Interpretation boundary

This is stronger than the rule-input proxy because the external pulse traverses
the full simulated neural network. It is still a controlled mechanistic
intervention, not a replacement confirmatory learning study and not evidence of
broad behavioral generalization.

The following remain locked regardless of numerical direction:

- `learning_validated=false`
- `full_network_reinforcement_pulse_causal=false`
- `temporal_credit_defect_confirmed=false`
- `causal_learning_claim_authorized=false`
- `replacement_confirmatory_authorized=false`
- `behavioral_promotion_authorized=false`

Human science review remains required before any causal claim can be promoted.
