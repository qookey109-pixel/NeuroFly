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

## Mode C — zero-cost segmented MaleCNS runtime

V0.4 adds a free alternative for users who do not want paid always-on hosting.

A public GitHub repository can use standard GitHub-hosted `ubuntu-latest` runners. NeuroFly uses those finite sessions as resumable experiment chunks:

```text
checkpoint N
    |
    v
GitHub Actions runner
    |
    v
MaleCNS decisions
    |
    v
checkpoint N+1
    |
    v
runner stops
```

This is **continuity across runs**, not a literal uninterrupted 24/7 operating-system process. The brain state and Maze state are restored on the next bounded run.

The free workflow is:

```text
.github/workflows/full-malecns-free.yml
```

It keeps prepared MaleCNS data in a separate cache from changing NeuroFly experiment state. Dataset cache saving is skipped above a 9 GB safety ceiling.

## Commands

Run headless on an adequate local machine:

```bash
python -m neurofly maze-run \
  --brain malecns \
  --checkpoint runs/maze-fly-001/brain.npz
```

Run the website and API from the same process:

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

NeuroFly checkpoints two coordinated pieces of state:

1. the brain checkpoint (`brain.npz` for MaleCNS);
2. the Maze world state (`brain.maze.json`).

The Maze checkpoint includes the current episode, fly position/direction, enemies, remaining food, reward totals, power state and Python RNG state. On process restart or the next segmented free run, the world resumes from the saved state rather than silently starting a fresh experiment.

Checkpoint writes for the Maze JSON use a temporary file followed by an atomic replace.

## Real MaleCNS prerequisites

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[stonkfly]'
python -m stonkfly prepare
python -m neurofly brain-status
```

The pinned Stonkfly preparation verifies source checksums and the retained graph. Upstream recommends 16 GB RAM and several GB of storage for the full retained MaleCNS workload.

## API

The persistent server exposes:

```text
GET  /api/status
GET  /api/state
POST /api/control
```

`POST /api/control` supports pause/resume, reset and decision cadence changes. CORS headers are emitted so a GitHub Pages viewer can observe a separately hosted backend.

## Zero-cost policy

NeuroFly V0.4 does not include a paid Render deployment template. The default operational path is:

- **GitHub Pages** — free static viewer;
- **standard GitHub Actions runner** — free bounded full-MaleCNS execution for this public repo;
- **GitHub Actions cache** — prepared data and resumable experiment state within cache limits;
- **small evidence artifacts** — receipts only, short retention.

An always-on machine remains optional if one is already available without additional cost.

## Validation boundary

Normal CI validates:

- Python package/runtime contract;
- the headless Maze loop using `DemoBrain`;
- persistent server startup;
- `/api/status` and `/api/state` responses;
- JavaScript syntax and static-site serving;
- checkpoint/restore of Maze world state;
- free-runner workflow safety.

The separate free full-MaleCNS workflow is the only GitHub Actions path intended to download/prepare the real connectome and produce a `FULL_MALECNS_SMOKE_PASS` receipt.
