# V0.11 Proprioception — live receptor observability

Status: **HUMAN-ONLY LIVE DIAGNOSTICS / REVIEW_REQUIRED**

This stage is stacked on the polarity-agnostic control-plane observability work. It makes the existing FeCO engineering receptor channels visible to a human observer without authorizing any systematic-type routing, current calibration, or proprioceptive stimulation.

## Goal

Show the exact receptor-domain proprioception payload used for the latest neural handoff:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

These remain engineering proxy channels produced by the representative virtual FeCO body.

## Timing rule

The website must not display `pending_proprioception` directly, because that payload belongs to the **next** neural decision.

`GoalMazeSession` therefore freezes `last_observed_proprioception` immediately after the pending receptor payload passes validation and immediately before the neural handoff. Human diagnostics are derived from that frozen copy.

This gives the invariant:

```text
human_diagnostics.proprioception.channels
==
context.proprioception.channels used by the latest neural handoff
```

The post-action pending pulse may already differ, and that difference is intentional.

## Human diagnostics boundary

The snapshot publishes only:

- receptor model and encoding;
- the four bounded receptor channel levels;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`;
- `systematic_type_mapping_exposed=false`.

It does not publish private body or privileged simulator state such as:

- joint position;
- joint phase;
- raw joint delta;
- executed motor command;
- world velocity or displacement;
- desired action.

It also contains no SNpp39/SNpp41 candidate mapping. Systematic-type hypotheses remain in the separate control-plane semantic snapshot introduced by the previous stage.

## Website separation

The HUD presents two visibly distinct blocks:

1. **LIVE RECEPTOR INPUT** — current engineering receptor levels from the latest neural handoff.
2. **CONTROL PLANE** — unresolved SNpp39/SNpp41 evidence semantics and hard locks.

The first does not derive systematic-type identity. The second does not become neural input.

## Fail-closed behavior

The live receptor panel refuses to render channel values unless all of the following hold:

- source is `latest-neural-handoff-receptor-domain`;
- model is the expected FeCO motion proxy;
- encoding is the expected virtual-joint motion proxy;
- all four channel values are finite and within `[0,1]`;
- stimulation remains disabled;
- runtime transduction remains disabled;
- systematic-type mapping exposure remains false.

If any condition fails, the panel reports `FAIL CLOSED` and hides the levels.

## Scope

- human-only live diagnostics;
- no new sensory mechanics;
- no systematic-type runtime binding;
- no SNpp39/SNpp41 current;
- no calibration unlock;
- no decoder/reward/learning change;
- no automatic merge.
