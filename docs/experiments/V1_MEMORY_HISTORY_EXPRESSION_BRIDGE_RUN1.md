# V1 Reward Memory History → Expression Bridge — Run 1

## Status

**EXPLORATORY MEMORY HISTORY EXPRESSION BRIDGE COMPLETE**

Successful GitHub Actions run: `36104612747`

- scientific head: `ed0bba7f1d9373c9bfa6ad28cd699216cb9e4c17`
- artifact id: `10850744135`
- artifact digest: `sha256:45cf654bcceda452564a731b60ef84bdcc1b7f51c8ffa72cd26bdbb8f9bbc863`
- receipt digest: `f61d6b9078cb43e80fdcf2bace26034cdb2b362739fd91119c450d54bf14162a`
- source checkpoint: `b4af753be2ad382ae112c9a4ee05198b15dc629b74d9a64e22d48edf8d7ae618`

The production checkpoint was unchanged. All preregistration and evidence gates
passed.

## Fair comparison

The 3 tau condition replayed exact lags `-60 ... 0`; the 1 tau condition
replayed exact lags `-20 ... 0`.

The primary expression comparison remained restricted to the identical
`-20 ... 0` terminal window. The 3 tau-only prefix `-60 ... -21` was
context warmup only and did not add extra primary success opportunities.

Changed reward edges were fixed before recall from the paired reward/no-pulse
synaptic difference.

## Primary result

Across four fresh trajectories, the mean number of changed reward edges was
`1505.75`.

Presence-level endpoints:

| Common terminal window | 1 tau | 3 tau |
| --- | ---: | ---: |
| any changed-KC activity | 4 / 4 | 4 / 4 |
| any MBON07 state difference | 4 / 4 | 4 / 4 |
| any MBON07 spike difference | 3 / 4 | 4 / 4 |
| any action divergence | 2 / 4 | 4 / 4 |
| reward-cue action divergence | 0 / 4 | 0 / 4 |

The longer history therefore did not merely turn a completely silent pathway
into an active one. Both conditions eventually reached changed KCs and MBON07
state in all four trajectories.

The major difference was **continuity and downstream expression across the
same terminal window**.

## Common-window continuity

Derived from the preregistered per-lag endpoints only:

| Descriptive measure over lags -20...0 | 1 tau | 3 tau |
| --- | ---: | ---: |
| mean changed-KC active fraction | 0.148842578027 | 0.328761877451 |
| mean changed-edge L1 engaged fraction | 0.224429760617 | 0.492223309279 |
| mean MBON07-state-difference lags / replicate | 9.75 / 21 | 21 / 21 |
| mean MBON07-spike-difference lags / replicate | 1.0 / 21 | 7.0 / 21 |
| mean action-divergence lags / replicate | 2.0 / 21 | 3.5 / 21 |

Most strikingly, the 3 tau condition already carried a paired MBON07 state
difference at lag `-20` in **4 / 4** trajectories and maintained an MBON07
state difference through every common terminal lag.

The 1 tau condition starts from a cleared transient state at lag `-20`, so
its expression builds later and heterogeneously.

This is exactly the mechanism the longer-history comparison was designed to
test: whether context established before the last 20 decisions changes the
expression state during the otherwise identical terminal sequence.

## Reward cue remains insufficient as a behavioral readout

At lag `0`, decoded action divergence remained:

- 1 tau: **0 / 4**
- 3 tau: **0 / 4**

Mean reward-cue changed-KC activity was:

- 1 tau: `0.381197938342`
- 3 tau: `0.355791845074`

Mean reward-cue changed-edge L1 engagement was:

- 1 tau: `0.565553626018`
- 3 tau: `0.510345133881`

Therefore the 3 tau effect must **not** be described as a stronger
instantaneous reward cue. Its evidence is the more stable temporal expression
state across the sequence.

## Replicate-level downstream expression

- **HE1 / 3109:** action divergence under both windows; 1 tau at `-2,-1`,
  3 tau at `-9`.
- **HE2 / 3119:** no 1 tau action divergence; 3 tau diverged at
  `-17,-11,-7`.
- **HE3 / 3121:** no 1 tau MBON07 spike or action divergence; 3 tau produced
  MBON07 spike differences and action divergence at
  `-12,-11,-9,-5,-3,-1`.
- **HE4 / 3137:** action divergence under both windows; 1 tau at
  `-15,-13,-9,-6,-5,-4`, 3 tau at `-12,-9,-8,-7`.

HE2 and HE3 are the strongest bridge examples: the same terminal sensory
sequence did not reach action divergence from a fresh 1 tau reset, but did so
when the earlier 40 decisions had first established temporal context.

## Interpretation

The current evidence chain is now:

`persistent paired KC→MBON07 synaptic difference`
→ reward-time eligibility depends materially on history older than 1 tau
→ 3 tau reconstructs eligibility more completely
→ 3 tau also creates a more continuous changed-KC / MBON07 expression state
through the common terminal window
→ downstream action divergence appears in more fresh trajectories.

This is strong exploratory support for a **history-dependent memory-expression
bridge**.

It is still not a validated learned behavior. In particular, the exact
reward-event cue remains behaviorally non-divergent in all fresh replicates.

## Next clean mechanism test

Before any behavioral confirmation or parameter tuning, test whether the extra
`-60 ... -21` context is **causally specific** rather than merely extra
runtime.

With fresh preregistered trajectories:

1. keep the exact same terminal `-20 ... 0` sequence in both conditions;
2. keep the exact 3 tau full-history condition;
3. replace or disrupt only the early `-60 ... -21` prefix using a frozen
   matched control defined before execution;
4. rebuild paired memory branches independently;
5. state-clear and freeze plasticity;
6. compare terminal KC / MBON07 / decoder expression with the same metrics.

This can distinguish sequence-specific temporal indexing from a generic effect
of allowing the network to evolve for 40 additional decisions.

## Claim state

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `cue_indexing_failure_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
