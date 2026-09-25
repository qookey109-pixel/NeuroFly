# V1 Reward Memory History → Expression Bridge Audit

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

KC trace-reconstruction run `36103039412` showed that replaying three frozen
KC-trace time constants (60 decisions) reconstructed substantially more of the
original reward-time changed-edge eligibility vector than replaying only one
time constant (20 decisions).

The mean changed-edge L1 overlap increased from approximately `0.2863` to
`0.8072`, and 3 tau had higher L1 overlap in all four fresh trajectories.
That result did **not** test whether the better-reconstructed temporal state
also makes the stored reward-memory difference express more reliably through
KC→MBON07 and downstream readout.

This audit tests that bridge.

## Frozen question

On the same fresh trajectory, does a **3 tau / 60-decision** prereward history
stabilize expression of the persistent paired reward-memory difference compared
with **1 tau / 20 decisions** after transient neural state is cleared?

The study remains exploratory. It has no directional pass threshold.

## Fresh trajectories

Four new seeds are frozen before execution:

- HE1 / 3109
- HE2 / 3119
- HE3 / 3121
- HE4 / 3137

For each seed, the selected event is the **first natural reward at or after
decision index 60**. Acquisition stops after the same five reinforcement-free
post-reward decisions used in the preceding memory-expression studies.

Maximum acquisition is 300 decisions. A seed with no qualifying reward is
invalid and is not replaced.

## Stored-memory construction

From one reconstructed pre-event checkpoint, the study creates paired branches:

- **no-pulse memory branch** — reward event replayed with no external
  reinforcement;
- **reward-memory branch** — the same event replayed with the frozen reward
  pulse.

Both branches then receive the same five reinforcement-free delay decisions.

Changed reward edges are defined **before recall** only by the paired synaptic
difference on the frozen reward compartment. Edge selection never depends on
later KC, MBON, decoder, or action outcomes.

The 1 tau and 3 tau comparisons each reconstruct fresh paired branches from the
same pre-event checkpoint. This prevents the longer replay from inheriting
state from the shorter replay.

## State-cleared recall

For every memory branch:

1. preserve synaptic memory;
2. clear transient neural state;
3. clear visual history;
4. disable learning;
5. freeze weights;
6. deliver no external reinforcement during recall.

The recall conditions are:

- **1 tau:** exact prereward lags `-20 ... -1`, then exact reward cue at
  lag `0`;
- **3 tau:** exact prereward lags `-60 ... -1`, then exact reward cue at
  lag `0`.

## Fair primary comparison

The 3 tau condition has 40 extra decisions of temporal context. Those extra
steps must **not** create 40 extra chances to count an expression event as a
success.

Therefore the primary 1 tau versus 3 tau comparison is restricted to the
identical terminal window:

`-20 ... 0`

The 3 tau-only interval `-60 ... -21` is retained in the receipt as context
warmup / mechanistic telemetry but is excluded from primary expression counts.

## Primary descriptive endpoints

Within the common terminal window, both conditions report:

- whether any changed presynaptic KC becomes active;
- changed-edge paired L1 engaged by active presynaptic KCs;
- whether any MBON07 state difference appears;
- whether any MBON07 spike difference appears;
- DNp20 / DNpe017 state differences;
- whether decoded action diverges;
- reward-cue action divergence at lag `0`;
- per-lag paired expression metrics for `-20 ... 0`.

The study reports the number of fresh replicates showing each observation under
1 tau and 3 tau. It does not predeclare a directional success threshold.

## Interpretation boundary

If 3 tau increases common-window KC / MBON07 expression, that would support the
narrow mechanism:

`more complete temporal eligibility context`
→ `more reliable expression of persistent synaptic memory`.

It would still **not** establish causal learned behavior.

If eligibility reconstruction improves but expression does not, the bottleneck
moves downstream or into additional state variables.

No tuning is permitted before interpreting this run:

- no decoder mapping/gain change;
- no reward-pulse change;
- no KC-threshold change;
- no MBON-weight change;
- no learning-rule change;
- no seed replacement;
- no post-hoc window selection.

## Governance

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `cue_indexing_failure_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
