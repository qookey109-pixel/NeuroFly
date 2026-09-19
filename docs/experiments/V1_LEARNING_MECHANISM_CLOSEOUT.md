# V1 Learning-Mechanism Diagnostic Closeout

Status: **LEARNING_MECHANISM_DIAGNOSTIC_CLOSED**

This document closes the current NeuroFly Maze learning-mechanism investigation.
It does **not** declare validated learning, successful confirmatory generalization,
or behavioral promotion.

## Why the branch can close

The diagnostic chain has now separated the major implementation and mechanism
questions far enough that adding more unplanned experiments would mostly become
post-hoc tuning rather than clean diagnosis.

The final event-local intervention is the closeout evidence.

### Event-Local Reinforcement Pulse Run #1

- Run: `35434647150`
- head: `55d346b0f0ac01af2ba8473a51a66faaf5e3cdcf`
- artifact: `10581628974`
- artifact digest:
  `sha256:61326964f7e25093a56a21a54f7260899d59c789de7b4310400600487cb38ca2`
- receipt:
  `6d7c7fc8c38106e8ceafb8e0346f87a7a6ae71cbfea59b2b3d9e372203e42712`
- execution valid: **true**
- all config/evidence gates: **PASS**

The design rebuilt each reinforced decision from an identical pre-event
checkpoint and compared one full-network true pulse against no external pulse.

Observed events:

| Type | Events | Negative pulse-minus-none efficacy | Positive | Mean efficacy difference |
| --- | ---: | ---: | ---: | ---: |
| reward | 14 | 14 | 0 | -0.000570152487 |
| aversive | 8 | 8 | 0 | -0.000468552113 |
| all | 22 | 22 | 0 | -0.000533206896 |

Pulse delivery was also visible in DAN output:

- reward-event reward-DAN spike increment: **+20.42857143**
- aversive-event aversive-DAN spike increment: **+1.0**
- immediate paired action divergence: **0.0**

Every observed event therefore had the same descriptive direction under this
frozen configuration: the true pulse branch ended the decision with a lower
mean efficacy delta than the no-pulse branch.

This is a controlled simulator observation. The formal
`single_event_reinforcement_effect_causal` claim remains locked false by
governance.

## Evidence chain

### 1. Original confirmatory run

Run `35323343414` produced `CONFIRMATORY_FAIL`.

Post-run audit found that nominal Maze seeds did not create independent enemy
trajectories under the old bounded execution semantics. The historical result
remains immutable and cannot be reinterpreted as an independent-replicate
generalization test.

### 2. Seed-effectiveness remediation

Decision-synchronous world stepping restored actual seed-dependent trajectories.
Exploratory remediation produced unique trajectories/checkpoints/evaluation
signatures across fresh seeds, removing the fake-independence defect.

Behavioral learning still remained poor.

### 3. Learning-mechanism diagnostic

The diagnostic found:

- checkpoint integrity was working;
- external outcome reinforcement reaches the brain on the next decision;
- learning-enabled `none` arms still changed memory on nearly every step;
- endogenous DAN activity was therefore materially involved in ongoing
  plasticity even without task reinforcement.

These are observations, not a promoted causal-learning claim.

### 4. DAN baseline / trace investigation

A calibrated DAN baseline by itself caused a large positive efficacy drift.
Counterfactual replay on identical frozen neural trajectories showed that the
large shift was tightly associated with the coordinate mismatch between the
persisted DAN trace state and the newly applied baseline.

Trace recentering reduced the large positive drift by about 98% in the
intervention and about 99.8% in the frozen-trajectory counterfactual replay.

Formal causal claim flags remained locked.

### 5. Recentered reinforcement discrimination

Run `35419000124` produced positive aggregate held-out contrasts:

- true minus none: **+3.625 reward**
- true minus scrambled: **+1.625**
- true minus frozen: **+1.375**

But replicate consistency was weak and the aggregate was strongly influenced by
one replicate. That result was not sufficient for learning validation or a new
confirmatory study.

### 6. Rule-input external reinforcement increment

Run `35426688269` isolated an equivalent compact DAN-rate increment on frozen
neural trajectories.

The mean true-minus-endogenous final efficacy difference was:

`-0.000952124579`

All four replicates had the same negative direction.

Because this bypassed the nonlinear LIF response, it was not treated as a
full-network pulse result.

### 7. Full-network repeated pulse replay

Run `35429987465` sent the existing 20 ms / 20.0 reinforcement pulse through
the complete MaleCNS LIF path while keeping the sensory trajectory fixed.

Results:

- endogenous-only mean final efficacy delta: **+0.002529397607**
- true-external mean final efficacy delta: **+0.000252634287**
- true minus endogenous: **-0.002276763320**
- reward-DAN spike increment: **+20.83/event**
- paired action divergence across the 60-step replay: **33.33%**

Three of four replicate final contrasts were negative. Repeated pulses, however,
allowed neural-state divergence to accumulate across later decisions.

### 8. Event-local full-network pulse

The final event-local study removed that cumulative-history ambiguity.

Each event starts both branches from exactly the same pre-event checkpoint;
only the current pulse differs.

Result: **22/22 observed events had a negative pulse-minus-none immediate
efficacy difference**, with zero immediate action divergence.

That is sufficiently stable for the current mechanism investigation to stop
without adding another post-hoc experiment.

## Closeout interpretation

The current evidence supports the following narrow statements:

1. The configured external reinforcement pulse measurably drives the intended
   DAN populations in the retained MaleCNS simulation.
2. After baseline calibration and trace recentering, the current task pulse does
   not add a positive immediate mean-efficacy increment relative to no pulse in
   the event-local study.
3. In the event-local sample, every observed reward and aversive event shifted
   immediate mean efficacy in the lower direction relative to its identical
   no-pulse branch.
4. The earlier positive held-out behavioral aggregate therefore cannot by itself
   be used as evidence that the current reinforcement mechanism is a validated
   learning signal.

The evidence does **not** establish that all useful plasticity must increase
global mean efficacy. It also does not prove that a lower global mean efficacy
is intrinsically harmful. Those would require a separately preregistered
mechanistic question with edge-/compartment-specific endpoints.

## Governance after closeout

The following remain **false / locked**:

- `learning_validated`
- `true_reinforcement_discriminated`
- `single_event_reinforcement_effect_causal`
- `temporal_credit_defect_confirmed`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

No automatic follow-up experiment is authorized from this branch.

Do not tune `eta`, decoder thresholds, pulse current/duration or task reward
thresholds merely to reverse these results. A future learning study must start
from a new explicit question and preregistration.

## Project-level consequence

This closeout ends only the **current learning-mechanism diagnostic branch**.

It does not close NeuroFly as a whole. Other independent project gates remain,
including the unresolved FeCO `SNpp39` / `SNpp41` exact flexion-extension
polarity crosswalk.

Machine-readable closeout state is frozen in
`data/learning_mechanism_closeout_v01.json`.
