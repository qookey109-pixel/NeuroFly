# NeuroFly 24/7 Runtime

NeuroFly separates the **viewer** from the **brain runtime**.

## Mode A — browser demo

The static `site/` visualizer can be hosted continuously on GitHub Pages. The autonomous demo simulation runs in JavaScript inside the visitor's browser.

This means:

- the public website can stay online 24/7;
- the demo starts when somebody opens the page;
- closing/suspending the browser stops that local simulation;
- it is useful for UI, environment and adapter validation;
- it is not persistent training.

## Mode B — persistent NeuroFly brain

For a fly that keeps accumulating experience while nobody is watching, run the connectome simulation as a separate always-on process.

```text
GitHub Pages / visualizer
          |
          | read live state
          v
     NeuroFly API
          |
          v
  Always-on Brain Worker
  Python + native kernel
          |
     +----+-----+
     |          |
 checkpoint   metrics/events
     |          |
     v          v
 persistent state store
```

The worker owns simulation time, episodes, rewards, neural state and checkpoints. The website is only an observer/controller and may disconnect at any time without stopping the experiment.

## Requirements for persistent experiments

A production-like experiment should support:

1. deterministic experiment configuration and seed;
2. periodic brain-state checkpoints;
3. resumable episodes after process restart;
4. append-only reward/action/event logs;
5. health checks and automatic process restart;
6. bounded disk usage and checkpoint retention;
7. explicit version pins for MaleCNS preprocessing and the simulation kernel;
8. a clear separation between simulated rewards and any real-world side effects.

Stonkfly's current README recommends several GB of storage and 16 GB RAM for its retained MaleCNS runtime. NeuroFly should therefore treat the full connectome worker as a backend workload rather than assuming it will fit comfortably in every browser or laptop.

## Hosting direction

The first deployment target should keep the architecture simple:

- **GitHub Pages** — static visualizer;
- **always-on Linux host / VPS** — NeuroFly brain worker;
- **small API or WebSocket/SSE bridge** — live state to the website;
- **local files or a small database/object store** — checkpoints and experiment history.

GitHub Actions remains CI/deployment automation, not the always-on simulation host.

## Current status

The v0.2 Maze Chase website is Mode A. It intentionally labels its controller as `Demo Agent` and does not claim the displayed telemetry is MaleCNS activity.

The next runtime milestone is Mode B: connect the same Maze Chase environment to the pinned MaleCNS-derived runtime and stream real experiment telemetry to the visualizer.
