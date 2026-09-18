# V0.12 — Multi-Environment Platform Dashboard

## Purpose

The original NeuroFly web console is tightly coupled to Maze Chase. That is
appropriate for the current production experiment but is not sufficient for a
v1 platform that can host multiple games.

This stage adds a parallel environment-agnostic dashboard without replacing the
existing Maze HUD.

## Runtime path

The platform path is:

EnvironmentSession
→ PlatformService
→ /api/platform/state
→ platform.html / platform.js

The same service can run either:

- Maze Chase
- Light Chase

using the EnvironmentAdapter contract introduced in the previous stage.

## State authority

The platform API explicitly marks its payload as:

- public_evaluation_state = true
- neural_input_authority = false

The dashboard is allowed to render world truth such as a maze grid or a Light
Chase target position because those fields are useful for humans, evaluation
and debugging.

Those fields do not become legal neural input.

The nested sensory_contract is still produced by the sensory-only environment
adapter and remains subject to the privileged-context firewall.

## Dashboard rendering

Maze Chase uses a top-down public renderer with:

- maze walls
- food
- enemies
- fly position

Light Chase uses a top-down public renderer with:

- bounded arena
- agent position
- light target

This is deliberately different from the neural visual frame. Human
visualization and neural perception are separate concerns.

## Shared telemetry

The dashboard exposes environment-independent fields when available:

- environment model
- brain backend
- episode
- current action
- reward
- event
- neural simulation time
- compute time
- total spikes
- gate spikes
- sensory contract summary
- runtime state

Environment-specific fields remain inside public state and are interpreted only
by the renderer for that environment.

## CLI

Start Maze through the platform path:

neurofly platform-server --environment maze --brain demo

Start Light Chase through the same path:

neurofly platform-server --environment light --brain demo

Default platform page:

http://127.0.0.1:8877/platform.html

The existing maze-server command and site/index.html are retained unchanged so
this work does not replace the current production UI.

## API

GET /api/platform/status

GET /api/platform/state

POST /api/platform/control

The control endpoint currently changes runtime execution state and tick
interval only. It does not inject actions, targets, rewards or sensory values.

## Completion meaning

Passing CI means that two different NeuroFly games can be observed through the
same server/API/dashboard layer while retaining a strict separation between:

- simulator/public world truth
- sensory-domain neural observation

It does not prove that MaleCNS has learned either environment and does not
change production authority.
