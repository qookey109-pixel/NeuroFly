# V1 Event-Local Reinforcement Pulse

Status: **EXPLORATORY INTERVENTION ONLY**

This study follows Full-Network Reinforcement Pulse Replay Run #1
(`35429987465`, receipt
`b74c77cd32ce848a923f7a548f043c7dd9bc5fe6ad3c611bd44a365d1a05a001`).

## Why this study exists

The previous full-network paired replay kept the sensory trajectory fixed, but
repeated pulse-versus-none decisions caused the two learning networks to diverge
in internal state and decoder output over later decisions. That makes the final
60-decision efficacy contrast informative but not fully event-local.

This study asks a narrower question:

> Starting from the exact same pre-event neural checkpoint, what immediate
> plasticity difference is produced by one true reward or aversive pulse versus
> no external pulse?

## Design

For each fresh trajectory seed:

1. A frozen MaleCNS driver records 60 synchronous maze decisions and the true
   incoming task-reinforcement schedule while receiving no external pulse.
2. Every decision whose recorded incoming reinforcement is `reward` or
   `aversive` becomes an independent event.
3. For each event, a learning-enabled MaleCNS is rebuilt from the production
   source and replays all earlier recorded sensory decisions with
   `reinforcement="none"`.
4. That exact pre-event state is checkpointed once.
5. Two branches restore from the same pre-event checkpoint:
   - `none`: current event frame/context, no pulse;
   - `true_external`: same frame/context, recorded true pulse.
6. Only the immediate one-decision difference is compared.

Fresh seeds: `2179, 2183, 2203, 2207`.

The paired branches use the existing calibrated DAN baseline and trace
recentering transform. Pulse duration/current, eta, decoder threshold, task
reward mapping and production checkpoint are not tuned.

## Primary descriptive endpoints

- total independent event count;
- reward-event true-minus-none efficacy delta;
- aversive-event true-minus-none efficacy delta;
- reward-DAN spike increment on reward events;
- aversive-DAN spike increment on aversive events;
- immediate event action-divergence fraction.

## Interpretation boundary

This design removes cumulative pulse-history divergence and isolates the immediate
effect of one recorded task reinforcement event from an identical pre-event
checkpoint. It is still an exploratory mechanistic intervention, not replacement
confirmatory authority.

All claims remain locked:

- `learning_validated=false`
- `single_event_reinforcement_effect_causal=false`
- `temporal_credit_defect_confirmed=false`
- `causal_learning_claim_authorized=false`
- `replacement_confirmatory_authorized=false`
- `behavioral_promotion_authorized=false`

If this event-local experiment yields a stable direction with successful pulse
delivery, the learning-mechanism investigation can move to synthesis/closeout.
Only materially inconsistent results justify one additional validation layer.
