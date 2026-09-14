# V0.10 Neural Context Firewall — Session Integration

Status: normal-session integration candidate; direct prepared smoke callers remain legacy until migrated separately.

## What changes

For non-demo session backends, `GoalMazeSession` no longer hands the complete environment snapshot to `brain.decide()`.

The new handoff is:

```text
world snapshot / fly / enemies
        |
        +--> human diagnostics
        |
        +--> sensory transducers
                |
                +--> retinal RGB
                +--> bilateral odor channels
                +--> JO-C/E channels
                +--> taste
                +--> touch
                +--> delayed FeCO proprioception
                         |
                         v
                 neural-context firewall
                         |
                         v
                    brain.decide
```

## Olfaction

`CurriculumMazeEnvironment.snapshot()` intentionally keeps diagnostic odor source coordinates and distances. They are now projected through `olfaction_neural_payload()` before the brain handoff. The neural side receives only bounded bilateral food/danger intensity channels.

## Vision

The existing `retinalize_topdown_rgb()` algorithm is executed before the brain decision call. `fly` and `enemies` stay on the transducer side.

The existing `MaleCNSBrain` still contains its older visual adapter for backward compatibility with direct prepared tests. In the normal session path it receives no `fly/enemies`; therefore it cannot use world geometry from context. Human visual diagnostics are reattached only to returned telemetry after the decision.

This is an integration step, not the final deletion of the legacy visual adapter.

## Demo baseline

`DemoBrain` remains an explicitly privileged lightweight baseline and continues to receive the old environment context. It is not the MaleCNS neural agent and is not evidence for biological behavior.

## Lightweight tests

The repository's normal unit-test dependency set intentionally does not install NumPy/Pillow. The firewall therefore has an identity-frame fallback only when the visual optional dependencies are absent. The context is still sanitized and vision is marked unavailable. In production MaleCNS/Stonkfly paths the visual dependencies are present and retinalization must execute; malformed frames still fail rather than falling back.

## Remaining legacy surface

Prepared runtime smoke workflows currently call `MaleCNSBrain.decide()` directly with environment snapshots. They are intentionally not changed in this PR. The next migration should route those direct prepared calls through the same firewall, then remove/deprecate `fly/enemies` consumption from `MaleCNSBrain._visual_input()` itself.
