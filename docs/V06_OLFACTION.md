# V0.6 Virtual Olfaction Contract

NeuroFly V0.6 adds an engineered game-to-connectome olfactory adapter while keeping sensory cues separate from reinforcement outcomes.

## Mapping

- Food odor cue -> MaleCNS `ORN_DM1` (`Or42b` proxy)
- Enemy danger odor cue -> MaleCNS `ORN_DA2` (`Or56a` / geosmin-like proxy)
- Eating food -> reward reinforcement
- Enemy capture -> aversive reinforcement

The game objects do not literally emit these molecules. These ORN mappings are virtual sensory proxies selected to provide biologically motivated appetitive and aversive channels inside the retained MaleCNS graph.

## Bilateral policy

NeuroFly never infers ORN side from body id or geometry. It resolves left/right in this order:

1. curated `somaSide` when populated;
2. curated annotation `instance` suffix `_L` / `_R` as fallback;
3. leave unresolved neurons unresolved.

The first real V0.6 MaleCNS evidence resolved:

- `ORN_DM1`: 74 total; 35 left, 39 right, 0 unresolved;
- `ORN_DA2`: 48 total; 21 left, 20 right, 7 unresolved.

For this dataset the resolved bilateral ORNs came from curated instance suffixes because `somaSide` was not populated for these sensory neurons.

## Sensory field

The game computes a bounded virtual odor field from authoritative environment state. Food and danger each expose left/right intensity. Intensity decays with distance and is modulated by source position relative to the fly's current heading. The adapter provides a directional cue only; it never provides a target action, path, or answer.

The selected current is applied to the matching left/right ORN groups during every MaleCNS neural bin. Visual R8 stimulation remains active in the same `rgb_step` call.

## Reinforcement stays separate

A food odor is not a reward. An enemy odor is not an aversive event.

- odor = cue;
- food consumption = reward;
- capture = aversive reinforcement.

This separation is required so later experiments can test whether the retained network/plasticity learns a relationship between a cue and an outcome rather than receiving the outcome merely for sensing the cue.

## First real-gate result

The first fully verified V0.6 olfactory gate used 12 real MaleCNS decisions and produced a `neurofly-self-training-v3` receipt with `neurofly-virtual-olfaction-v1` telemetry. The run passed the real graph, bilateral ORN, neural activity, world-state, receipt-integrity, state-publish, checkpoint and evidence gates.

Receipt SHA-256:

`93d64edbb47ebe3a950c2a59276194c60cf231f6e8d55443cca158c17bcd2541`

At the end of that evidence batch:

- curriculum stage: 1 `food-corridor`;
- food eaten in the stage: 0;
- clears: 0;
- deaths: 0;
- final decision food cue: left 0.879469 / right 0.333592;
- final decision food-ORN spikes: 2,590;
- final decision danger-ORN spikes: 88 while danger cue current was zero;
- final memory: 3,413 changed edges out of 7,835 plastic edges.

The nonzero danger-ORN spike count with zero danger cue is important: spike count alone is not causal proof of odor stimulation because the recurrent network has background/network-driven activity.

The same batch ate no food and did not clear Stage 1, so V0.6 does **not** yet claim that MaleCNS learned to follow food odor. That remains the behavioral training target.

## Controlled calibration protocol

Before interpreting odor spike magnitude, NeuroFly runs a frozen-plasticity matched-state calibration. Every condition starts from the same restored checkpoint, uses the same fixed Stage 1 RGB frame, receives no reward or aversive reinforcement, and changes only the virtual odor input.

Conditions:

1. `odor_off` — food 0 / danger 0;
2. `food_left` — food left 1 / right 0, danger 0;
3. `food_right` — food left 0 / right 1, danger 0;
4. `danger_left` — danger left 1 / right 0, food 0;
5. `danger_right` — danger left 0 / right 1, food 0.

Primary evidence:

- target ORN spike delta versus `odor_off`;
- ipsilateral versus contralateral target ORN activity, normalized per resolved neuron;
- off-target ORN change;
- downstream DNp20/DNpe017 and total-spike changes;
- exact checkpoint identity and Stonkfly pin;
- unchanged plastic-memory SHA before/after each condition;
- unchanged checkpoint file SHA before/after the workflow.

Pass criteria require a positive target-channel delta above baseline and the intended stimulated side to exceed the unstimulated side. This calibration validates the engineered sensory transduction only; it does not by itself demonstrate navigation learning.

## Matched-state calibration result

Workflow run `34666021865` completed successfully using the V0.6 state restored from `neurofly-v06-state-34665588617-1`.

Checkpoint SHA-256 before and after calibration:

`6742941f70507fddc0018c87d95a9a6c5ecbb5bec24fe3c5a4fae2f7c5a19a9b`

Calibration receipt SHA-256:

`c211d1c6857018c8c50f825b71a554b565f78304a7d700b91e0475ea377d9f76`

All four unilateral target-channel gates passed:

| Condition | Baseline target spikes/neuron | Stimulated target | Contralateral | Delta vs baseline | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `food_left` | 11.942857 | 37.057143 | 28.487179 | +25.114286 | PASS |
| `food_right` | 19.769231 | 44.923077 | 20.400000 | +25.153846 | PASS |
| `danger_left` | 2.380952 | 22.428571 | 2.650000 | +20.047619 | PASS |
| `danger_right` | 1.700000 | 20.800000 | 4.190476 | +19.100000 | PASS |

Interpretation: under a matched checkpoint, fixed visual frame, frozen plasticity and no reinforcement, adding the engineered food or danger odor current causally increased activity in the intended ORN channel and the intended side exceeded the contralateral side in every tested condition. The V0.6 game-to-ORN sensory transduction is therefore validated for this experiment.

This result does **not** show that MaleCNS has learned odor-guided navigation. Behavioral evidence still requires food acquisition and maze clears during self-training, followed by held-out controls.
