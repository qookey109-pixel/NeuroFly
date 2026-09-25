# V1 Reward Memory Boundary-State Localization — Run 1

## Status

**EXPLORATORY MEMORY BOUNDARY-STATE LOCALIZATION COMPLETE**

Successful GitHub Actions run: `36108551430`

- scientific head: `f64ccc958a15859fd368e8f2d58e313114a234f3`
- artifact id: `10852801468`
- artifact digest: `sha256:7a052e634fd944eb3204f1aa45a70b76366a7941ca600e05cbbd03a3ad558128`
- receipt digest: `52b2d9cfe512e539c33a59899a0a6554cbc96455f249237bbd79eff04522ba91`
- source checkpoint: `e43ec25d407d465339911db388841a9b32effaa364d4354266e2332d22579c2b`

All preregistration/evidence gates passed. The production checkpoint was
unchanged.

## Intervention integrity

Every condition used the same paired synaptic memory, exact `-60 ... -21`
prefix, and exact `-20 ... 0` terminal sequence.

At the frozen boundary:

- `clear_rule_traces` changed only `rate_kc` and `rate_dan`;
- `clear_membrane_conductance` changed only `v` and `g`;
- `clear_wrapper_visual_history` changed only the wrapper visual-history
  cache;
- all interventions preserved synaptic memory.

## Main result

| Terminal `-20...0` measure | Intact | Clear rule traces | Clear visual history | Clear v/g |
| --- | ---: | ---: | ---: | ---: |
| changed-KC coverage | 3/4 | 3/4 | 3/4 | **4/4** |
| MBON07-state coverage | 3/4 | 3/4 | 3/4 | **4/4** |
| MBON07-spike coverage | 3/4 | 3/4 | 3/4 | **4/4** |
| action-divergence coverage | 3/4 | 3/4 | 3/4 | **4/4** |
| reward-cue action divergence | 0/4 | 0/4 | 0/4 | **1/4** |
| mean changed-KC active fraction | 0.252869236632 | 0.252869236632 | 0.252869236632 | **0.317367740445** |
| mean changed-edge L1 engaged fraction | 0.372283195681 | 0.372283195681 | 0.372283195681 | **0.470302395984** |
| mean MBON07 state-difference fraction | 0.750000000000 | 0.750000000000 | 0.750000000000 | **0.952380952381** |
| mean MBON07 spike-difference fraction | 0.142857142857 | 0.142857142857 | 0.142857142857 | **0.250000000000** |
| mean action-divergence fraction | 0.142857142857 | 0.142857142857 | 0.142857142857 | **0.226190476190** |

## Rule traces are not carrying frozen-recall expression

Clearing `rate_kc` and `rate_dan` produced an **exactly identical** result
to intact on every stored aggregate and every terminal per-lag endpoint.

That is consistent with their role in the centered plasticity rule: recall
plasticity is disabled and weights are frozen here.

This does not say those traces are unimportant for learning. It says they are
not the state carrying the already-stored paired-memory expression across this
frozen recall boundary.

## Wrapper visual-history cache is also neutral

Clearing `_last_visual_rgb` was also exactly identical to intact on all
aggregate and per-lag endpoints.

The wrapper visual cache therefore does not explain the 3 tau expression
advantage in this assay.

## Membrane / conductance state matters, but not as a positive carrier

Clearing only `v` and `g` strongly changed downstream expression. The
direction, however, was **enhancement**, not collapse.

Most notably:

- BL2 had no intact KC / MBON07 / action expression, but expression appeared
  after the v/g clear;
- BL1 acquired reward-cue action divergence at lag 0 after the v/g clear;
- all four fresh replicates showed KC, MBON07 spike and action expression after
  v/g clearing.

Therefore the accumulated `v/g` state is an expression **modulator** in this
assay, but it cannot be called the positive carrier of the extra-runtime
benefit. The observed direction is compatible with a suppressive or
state-dependent gating contribution.

## Updated mechanism picture

The evidence now says:

`persistent synaptic memory`
→ longer history improves later expression
→ exact early ordering is not strictly required
→ centered-rule traces do not carry frozen-recall expression
→ wrapper visual-history state does not carry it
→ membrane/conductance state modulates expression, but clearing it enhances
rather than abolishes expression
→ the positive extra-runtime carrier remains unresolved.

## Next localization layer

The remaining Stonkfly transient state should be split into single-class
boundary interventions before combinations are attempted.

Priority candidates:

1. synaptic-delay / refractory state:
   `refractory`, `queue`, `queue_count`, and closely coupled spike-history
   bookkeeping;
2. retinal adaptation/input state:
   `luminance`;
3. neuronal adaptation state:
   `adaptation`;
4. kernel eligibility / modulation state:
   `eligibility`, `eligibility_last`, `modulation`,
   `modulation_last`.

Each condition should keep the same paired memory, prefix, terminal sequence,
decoder and learning locks.

## Claim state

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
