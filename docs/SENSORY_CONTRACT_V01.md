# NeuroFly Sensory Contract v0.1

Status: implementation boundary / not a biological validation claim

## Core rule

NeuroFly must not receive the game world as truth.

The environment may know exact coordinates, paths, entity identities and future state for simulation and debugging, but the neural agent may only receive signals produced by fly-accessible sensory transduction.

```text
world truth
   |
   +--> human diagnostics / validation
   |
   `--> sensory transduction
           |
           `--> agent_input
                   |
                   `--> MaleCNS / controller
```

Only `agent_input` is eligible to affect neural stimulation or neural decisions.

## Why this boundary exists

A top-down maze, target coordinate, exact enemy bearing, source coordinate or solved route can silently turn a sensory experiment into ordinary game-state control. NeuroFly therefore treats those fields as privileged information even when they are useful for visualization or tests.

The contract is machine-checked by `assert_unprivileged_agent_input`.

## Contract identity

- schema: `neurofly-sensory-contract-v0.1`
- policy: `egocentric-no-privileged-world-state`
- implementation: `src/neurofly/sensory_contract.py`

## Active modalities

### Vision

Neural representation: `retinal-rgb-proxy`

The retained visual pathway receives the existing fly-centered retinal RGB proxy. JSON metadata declares the model and coordinate policy only; it does not pass exact enemy bearings, distances, wall coordinates or a top-down map into the neural input.

Human diagnostics may still report those values to verify the renderer and looming behavior.

### Olfaction

Neural representation: `bilateral-orn-current-proxy`

The neural payload contains only bounded left/right/intensity values for the existing food and danger odor channels.

Exact odor-source coordinates and metric distance remain diagnostics-only.

This preserves the existing MaleCNS bilateral ORN stimulation path while making the privilege boundary explicit.

## Reserved modalities

The following names are reserved in v0.1 but deliberately unavailable until a defensible biological mapping and transduction model are implemented:

- antennal mechanosensation / airflow;
- proprioception;
- contact mechanosensation;
- gustation;
- thermo/hygrosensation;
- polarized-light sensing.

Each reports:

```json
{
  "available": false,
  "status": "pending-biological-mapping"
}
```

This prevents a future adapter from silently inventing a neuron mapping merely to make a game easier.

## Privileged fields

The neural-input guard currently rejects world-truth fields including:

- `x`, `y`;
- `source`;
- `distance_cells`;
- `bearing_degrees`;
- `target`, `target_action`;
- `action`, `demo_action`;
- `grid`, `enemies`;
- `route`, `path`.

The diagnostics side may contain these when necessary for validation.

## Reinforcement boundary

Reward and aversive stimulation are outcome signals, not sensory truth. They remain temporally downstream of world events and must not be encoded into the sensory payload as a desired action or target label.

## Next implementation stages

1. Route runtime telemetry through the unified sensory contract without changing current MaleCNS stimulation semantics.
2. Add an explicit sensory-contract section to the browser HUD so users can see which modalities are active, reserved or diagnostics-only.
3. Research MaleCNS annotations and published Drosophila pathways for antennal mechanosensation and proprioception.
4. Add one new modality at a time with a versioned adapter, tests and evidence notes.
5. Keep the current visual and olfactory paths as regression baselines while expanding the stack.

## Scientific interpretation

`neurofly-sensory-contract-v0.1` is an engineering boundary that reduces privileged information leakage. It does not establish that the resulting agent has natural Drosophila perception, subjective experience, consciousness or a complete sensory reconstruction.
