# NeuroFly 24/7 Runtime

NeuroFly separates the **viewer** from the **brain/runtime authority**.

## Mode A — browser demo

The static `site/` visualizer can be hosted continuously on GitHub Pages. When no NeuroFly API is reachable, the page falls back to a JavaScript `Demo Agent`.

This means:

- the public website can stay online 24/7;
- the demo starts when somebody opens the page;
- closing/suspending the browser stops that local demo;
- it is useful for UI and environment validation;
- it is not persistent training.

## Mode B — persistent NeuroFly runtime

V0.3 implements the server-side loop needed for a fly that keeps running while nobody is watching.

```text
GitHub Pages / visualizer
          |
          | GET /api/state
          | POST /api/control
          v
     NeuroFly API
          |
          v
   MazeSession authority
          |
     +----+-------------------+
     |                        |
 Maze environment        Brain backend
     |                        |
     |                   demo | malecns
     |                        |
     +----------+-------------+
                |
          checkpoint pair
       brain.npz + brain.maze.json
```

The worker owns simulation time, episodes, rewards, world state and neural state. The website is an observer/controller and may disconnect without stopping the experiment.

## Commands

Run headless:

```bash
python -m neurofly maze-run \
  --brain malecns \
  --checkpoint runs/maze-fly-001/brain.npz
```

Run the website and API from the same always-on process:

```bash
python -m neurofly maze-server \
  --brain malecns \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint runs/maze-fly-001/brain.npz
```

The browser automatically detects a same-origin API. A separately hosted GitHub Pages viewer can connect with:

```text
https://qookey109-pixel.github.io/NeuroFly/?api=https://YOUR-BACKEND
```

## Persistence

V0.3 checkpoints two coordinated pieces of state:

1. the brain checkpoint (`brain.npz` for MaleCNS);
2. the Maze world state (`brain.maze.json`).

The Maze checkpoint includes the current episode, fly position/direction, enemies, remaining food, reward totals, power state and Python RNG state. On process restart the world resumes from the saved state rather than silently starting a fresh experiment.

Checkpoint writes for the Maze JSON use a temporary file followed by an atomic replace.

## Real MaleCNS prerequisites

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[stonkfly]'
python -m stonkfly prepare
python -m neurofly brain-status
```

The pinned Stonkfly preparation verifies source checksums and the retained graph. The full runtime requires several GB of storage and a C++17 compiler. Upstream currently recommends about 16 GB RAM for the retained MaleCNS workload.

## API

V0.3 exposes:

```text
GET  /api/status
GET  /api/state
POST /api/control
```

`POST /api/control` supports pause/resume, reset and decision cadence changes. CORS headers are emitted so a GitHub Pages viewer can observe a separately hosted backend.

## Hosting

A real 24/7 MaleCNS experiment requires an always-on machine or service with enough RAM, storage and persistent disk for checkpoints/data.

Recommended separation:

- **GitHub Pages** — static public viewer;
- **always-on Linux host / VPS / suitable container host** — `maze-server` or `maze-run`;
- **persistent disk** — MaleCNS prepared data and checkpoint pair;
- **process supervisor** — restart NeuroFly if the process exits.

GitHub Actions is used for CI/deployment automation and is intentionally **not** used as the permanent simulation host.

## Validation boundary

Normal CI validates:

- Python 3.11 and 3.12 package/runtime contract;
- the headless Maze loop using `DemoBrain`;
- persistent server startup;
- `/api/status` and `/api/state` responses;
- JavaScript syntax and static-site serving;
- checkpoint/restore of Maze world state.

CI deliberately does not download the multi-GB MaleCNS dataset. Therefore a green ordinary CI run does not claim that a full 166,700-neuron execution happened in GitHub Actions. A true MaleCNS run requires a prepared host and is tracked separately.
