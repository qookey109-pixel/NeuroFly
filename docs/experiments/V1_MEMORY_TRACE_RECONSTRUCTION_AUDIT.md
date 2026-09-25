# V1 Reward Memory KC Trace Reconstruction Audit

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

Temporal-index run `36095883843` established two facts that must remain
separate:

1. almost all KC→MBON07 edges changed by the paired reward pulse carried
   positive prereward KC eligibility at reward time; and
2. state-cleared replay of one trace time constant (20 decisions) re-expressed
   the changed-KC / MBON07 pathway in only a subset of trajectories.

The current run does not repeat that experiment. It asks why the 20-decision
replay was heterogeneous.

## Frozen question

How much of the **original reward-time KC eligibility vector** can be
reconstructed after transient-state clearing by replaying:

- **1 tau = 20 decisions**, versus
- **3 tau = 60 decisions**

of the exact prereward sensory history from the same trajectory?

The Stonkfly KC trace remains frozen at 1.0 second and NeuroFly advances 50 ms
per decision. Three time constants therefore equal 60 decisions. An
exponential trace has about 4.98% contribution remaining from history older
than 3 tau; this motivates the longer descriptive window without treating it as
a hard cutoff.

## Event acquisition

Four fresh seeds are frozen before execution:

- TR1 / 3001
- TR2 / 3011
- TR3 / 3019
- TR4 / 3023

The event is the **first natural reward at or after decision index 60**. This
guarantees a complete 60-decision prereward history.

Acquisition stops after the same five reinforcement-free post-reward decisions
used to define the paired synaptic difference. Maximum acquisition is 300
decisions. A seed with no qualifying reward is invalid and is not replaced.

No external reinforcement is delivered while recording the trajectory or
reconstructing prereward history.

## Target vector

For each trajectory, the original pre-event checkpoint is reconstructed exactly
as in the prior temporal-index audit.

Immediately before the selected reward, the audit freezes the reward-edge
`rate_kc` eligibility vector as the reconstruction target. The full vector is
bound by SHA-256; large raw vectors are not promoted into Git.

The changed-edge subset is defined independently from the paired
reward/no-pulse synaptic difference after the frozen five-decision delay. The
audit does not select edges based on reconstruction quality.

## Paired replay conditions

Two independent replay brains start from the same pre-event checkpoint.

For both:

1. preserve synaptic memory;
2. clear transient neural state;
3. clear visual history;
4. disable learning and freeze weights;
5. deliver no external reinforcement.

Then:

- **1 tau condition:** replay exact lags `-20 ... -1`;
- **3 tau condition:** replay exact lags `-60 ... -1`.

Both conditions use the same trajectory. No reward-event frame is replayed,
because the target is the eligibility state immediately **before** reward.

## Descriptive endpoints

For changed reward edges, every replayed lag reports:

- cosine similarity to the original target trace;
- L1 overlap fraction
  `sum(min(abs(target), abs(replay))) / sum(abs(target))`;
- normalized L1 error
  `sum(abs(replay-target)) / sum(abs(target))`;
- replay / target L1 ratio;
- recovery fraction among target-positive edges.

The final 1 tau and 3 tau states are compared descriptively on the same
trajectory, including the 3 tau minus 1 tau overlap delta.

The same metrics are also retained for the full frozen reward-edge vector as a
secondary localization check.

## Interpretation boundary

There is **no directional pass threshold** in this study.

A higher 3 tau reconstruction would support the narrower mechanism that the
20-decision replay omitted material eligibility history. It would not by itself
validate learning or a behavioral cue.

A failure of 3 tau to reconstruct the original vector would instead leave open
other explanations, including state-clear-dependent sensory dynamics or
additional internal temporal state.

The study must not change:

- decoder mapping or gain;
- reinforcement pulse;
- KC thresholds;
- MBON weights;
- learning parameters;
- seeds or event selection after observing results.

## Governance

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `cue_indexing_failure_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

This is eligibility-state mechanism localization only.
