# V0.10 Neural Context Firewall Contract

Status: contract / unit-test stage; not yet integrated into `GoalMazeSession` or `MaleCNSBrain`.

## Problem found during proprioception routing

The existing normal visual path renders a top-down debug/world frame and lets `MaleCNSBrain._visual_input()` receive `fly` and `enemies` from the decision context so it can call `retinalize_topdown_rgb()` internally.

The resulting neural image is egocentric retinal RGB, so the current system is not directly stimulating neurons from enemy coordinates. However, the architectural boundary is still too weak: world truth reaches the brain object before transduction.

NeuroFly's long-term rule is stricter:

```text
world truth
  -> sensory transducer
  -> neural-safe sensory payload
  -> MaleCNS
```

not:

```text
world truth -> MaleCNS wrapper -> sensory transducer inside wrapper
```

## Firewall v0.1

Schema:

`neurofly-neural-context-firewall-v0.1`

Policy:

`world-truth-stops-at-sensory-transducer`

The firewall accepts only already-transduced modality payloads:

- vision
- olfaction
- antennal mechanosensation
- proprioception
- contact mechanosensation
- gustation
- thermo/hygrosensation
- polarized light

Unknown top-level fields fail closed. The firewall does **not** silently strip `fly`, `enemies`, `demo_action`, route state, reward, or future unknown fields.

Nested payloads are also checked with the existing strict privileged-key guard.

## Visual handoff

`prepare_firewalled_visual_input()` has two explicitly separated inputs:

1. transducer-only world truth: `fly`, `enemies`, top-down rendered frame;
2. already-transduced nonvisual sensory context.

It runs the existing `retinalize_topdown_rgb()` unchanged. World geometry can remain in returned human diagnostics, but neural context receives only this declaration:

```json
{
  "model": "neurofly-compound-eye-proxy-v1",
  "available": true,
  "encoding": "retinal-rgb-proxy",
  "coordinate_frame": "egocentric-retina",
  "world_geometry_exposed": false,
  "engineered_proxy": true
}
```

The retinal RGB image travels separately as the frame.

## Important scope boundary

This PR does not yet change `MaleCNSBrain` or `GoalMazeSession`. It establishes the API and tests first so the integration can be reviewed independently.

The next stage should:

1. transduce the top-down frame before the neural decision call;
2. send the retinal frame plus firewalled sensory context to MaleCNS;
3. remove `fly/enemies` consumption from `MaleCNSBrain._visual_input()`;
4. preserve visual telemetry by keeping geometry under human diagnostics, outside neural context;
5. explicitly preserve the lightweight `DemoBrain` baseline separately rather than using its privileged `demo_action` as a precedent for neural agents;
6. update prepared runtime smoke workflows to use the same firewall path rather than direct world-state contexts.

## PASS meaning

A PASS validates the boundary contract and fail-closed behavior. It does not yet prove the normal runtime has stopped passing visual world truth into `MaleCNSBrain`; that claim requires the next integration PR.
