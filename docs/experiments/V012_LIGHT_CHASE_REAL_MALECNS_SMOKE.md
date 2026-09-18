# V0.12 — Real MaleCNS Light Chase Smoke

## Purpose

Light Chase is the second playable NeuroFly environment. Earlier stages prove
that its world, sensory adapter, generic EnvironmentSession and platform
dashboard are structurally valid.

This stage adds the first execution path that can prove the real MaleCNS backend
actually runs through that second environment.

## Scope

The experiment is deliberately narrow.

It asks:

Can an existing real MaleCNS brain checkpoint execute verified neural decisions
inside Light Chase through the shared sensory-only adapter?

It does not ask whether the brain has learned to seek the light.

## Execution

The manual workflow restores the current production brain checkpoint as a
read-only source.

The runner then:

1. records the source brain SHA-256;
2. copies the brain to an isolated Light Chase proof path;
3. restores MaleCNS from that isolated copy;
4. forces learning off and freezes weights;
5. creates LightChaseAdapter and EnvironmentSession;
6. executes the preregistered number of decisions;
7. requires every state to contain verified real MaleCNS neural activity;
8. requires every sensory context to pass the shared privileged-state firewall;
9. saves the proof brain and private Light Chase environment state;
10. verifies the production source SHA-256 is unchanged;
11. writes a compact hashed receipt.

## Neural boundary

The real MaleCNS process receives the Light Chase egocentric RGB sensory frame.

It does not receive:

- target coordinates;
- target bearing;
- target distance;
- route/path solution;
- recommended action.

The public receipt may report behavior and reward metrics for human review, but
those public fields are not neural input.

## Learning boundary

This smoke test runs with:

learning = false

and the underlying weights are explicitly frozen after checkpoint restore.

The purpose is execution compatibility, not training.

## PASS meaning

A PASS supports the statement:

A real MaleCNS backend restored from an isolated production-brain copy and
produced verified neural decisions in Light Chase through the shared NeuroFly
environment adapter.

## PASS does not mean

A PASS does not establish:

- successful light-seeking behavior;
- Light Chase learning;
- generalization;
- behavioral superiority over a control;
- promotion of Light Chase into the production training curriculum.

Those claims remain locked.

## Isolation

The workflow does not:

- overwrite the production brain;
- save the proof brain into production cache;
- push main;
- dispatch continuous training;
- upload the proof brain checkpoint.

Only compact preflight and execution-receipt evidence are uploaded.
