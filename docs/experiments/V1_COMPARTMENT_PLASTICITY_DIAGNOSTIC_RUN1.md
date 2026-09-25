# V1 Compartment Plasticity Diagnostic — Run 1

## Status

**EXPLORATORY DIAGNOSTIC COMPLETE**

Successful GitHub Actions run: `36090134339`

Receipt:

`19802e5a95243b55f1712b313e6e844637a85eff4c35e405d8d4b8a936e71308`

Artifact digest:

`sha256:5e7c347af0adc0d4dad1b94812012413423d5ac34d48e319eb9920b61c25f8be`

The production checkpoint SHA was identical before and after the study:

`3ae3317d452ea48ea04584836d6b99ec4133e0663dbd48615364c4735c0f8082`

## Invalid first execution

Run `36089897219` is not scientific evidence.

It stopped during implementation validation because a fixed `1e-10`
weight-to-`memory_w` reconstruction tolerance was too strict for the
checkpoint's finite-precision weight dtype versus the higher-precision memory
state.

The fix used a machine-epsilon-derived, dtype-aware quantization bound. It did
not change the preregistered:

- seeds;
- event definition;
- pulse duration/current;
- learning rate;
- DAN baseline;
- trace recentering;
- edge compartments;
- endpoints;
- interpretation or claim policy.

The corrected run passed the reconstruction gate.

## Execution integrity

All config gates and all evidence gates passed.

The study used four fresh trajectory seeds:

- C1 / 2309: 3 reinforced events
- C2 / 2311: 3 reinforced events
- C3 / 2333: 7 reinforced events
- C4 / 2339: 3 reinforced events

All four trajectory digests were distinct.

Frozen plastic topology:

- total KC→memory-MBON plastic edges: **7,835**
- PAM11/MBON07 reward compartment: **3,651**
- PPL101/MBON11 aversive compartment: **4,184**
- overlap: **none**

## Observed result

Across **16 paired natural task events**:

- reward events: **15**
- aversive events: **1**
- immediate action divergence between no-pulse and true-pulse branches: **0%**

### Reward events

Across 15 reward events:

- mean target-compartment L1 fraction: **1.0**
- median target-compartment L1 fraction: **1.0**
- target-dominant event fraction: **1.0**
- mean target signed efficacy delta: **-0.001273467775222**
- mean target absolute delta: **0.001273482385779**
- mean off-target absolute delta: **0**
- maximum off-target absolute delta: **0**
- mean fraction of target edges with negative change: **0.407778690769**
- mean fraction with positive change: **0.000036519675**

### Aversive event

The single observed aversive event showed:

- target-compartment L1 fraction: **1.0**
- target-dominant: **true**
- mean target signed efficacy delta: **-0.001020820100972**
- mean target absolute delta: **0.001020820100972**
- mean off-target absolute delta: **0**
- maximum off-target absolute delta: **0**
- target negative-edge fraction: **0.451003824092**
- target positive-edge fraction: **0**

## Interpretation

The earlier negative global mean efficacy effect should no longer be described
as broad, nonspecific drift across both memory compartments.

Under the current frozen Stonkfly rule, a true reinforcement pulse changes only
the compartment preselected by the circuit gain topology:

- reward pulse → reward compartment;
- aversive pulse → aversive compartment.

No off-target paired efficacy effect was detected in this execution.

This is important mechanistic clarification, but it is also structurally
consistent with how the frozen gain matrix routes DAN effects. It therefore
validates the implementation-level compartment behavior; it does **not**
independently validate the biology or prove useful learning.

The paired pulse effect was predominantly negative within the target
compartment, and it produced no immediate action divergence.

Although the four complete trajectory digests differ, several reinforced event
times and paired effects repeat across seeds. This exploratory study therefore
makes no replicate-independence or generalization claim.

## Claim state

All remain false:

- `learning_validated`
- `compartment_specificity_causal`
- `reinforcement_mechanism_validated`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

## Next preregistered question

The next useful learning question is no longer whether the pulse reaches the
correct compartment. It does.

The remaining question is whether that compartment-local edge change **persists
and changes later cue-conditioned behavior**.

The next study should therefore use a new paired recall design:

1. identical pre-event checkpoint;
2. no-pulse versus true-pulse branch at one natural event;
3. no further reinforcement;
4. fixed post-event delay;
5. identical replayed sensory cue;
6. compare compartment memory persistence and neural/action response.

That study must be preregistered separately and must still keep
`learning_validated=false` until a later confirmatory design is justified.
