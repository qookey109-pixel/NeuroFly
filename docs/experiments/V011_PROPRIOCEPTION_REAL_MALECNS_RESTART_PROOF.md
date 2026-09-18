# V0.11 Proprioception — Real MaleCNS Restart Proof

## Purpose

PR #84 proves that the production self-training orchestration path is restart
stable under a deterministic CI fixture. It deliberately does not claim that a
real MaleCNS Python process exited and a second real MaleCNS process restored
the same checkpoint.

This stage defines that stronger operational proof.

## Execution shape

The dedicated manual free-runner workflow uses a **copy** of the latest
production checkpoint:

```text
latest production checkpoint
        |
        | copy only
        v
runs/restart-proof/brain.npz
        |
        v
Process A: real MaleCNS training
        |
        | save + exit
        v
SHA-256 brain.npz + brain.maze.json
capture _pending_proprioception
        |
        | verify files unchanged
        v
Process B: new Python process
        |
        | restore same files
        v
first verified neural handoff
        |
        v
exact receptor comparison + receipt
```

The proof does not save its checkpoint back to the production cache, publish
state to `main`, or dispatch another training run.

## Required evidence

Both process A and process B must independently emit valid
`neurofly-self-training-v3` receipts with:

- `backend = malecns`;
- `neural_activity_verified = true`;
- a valid receipt SHA-256;
- at least one trajectory state;
- positive neural spike count on the first published state.

Process A must produce the coordinated checkpoint pair:

- `brain.npz`;
- `brain.maze.json`.

The SHA-256 values of both files immediately after process A exits must equal
their values immediately before process B starts.

Process B must be a separate Python child process.

## Proprioception continuity criterion

After process A exits, the private Maze checkpoint contains the receptor payload
that is pending for the next neural decision:

`_pending_proprioception`.

That payload is inspected by the proof harness only. It must pass the global
unprivileged sensory guard.

The first public/current proprioception handoff emitted by process B must be
**exactly equal** to that pending receptor payload.

This is the key proof that a real process boundary does not invent, drop or
change the next proprioceptive sample.

## State continuity checks

The proof also requires:

- process B `clears_before` equals process A `clears_after`;
- final clear count is non-decreasing;
- final death count is non-decreasing;
- final world tick count is non-decreasing.

These are operational continuation checks, not behavioral performance claims.

## What a PASS means

A PASS supports the narrow statement:

> A real MaleCNS training process saved a coordinated NeuroFly checkpoint,
> exited, and a second real MaleCNS Python process restored that exact
> checkpoint pair and received the expected next proprioceptive receptor
> handoff while continuing verified neural execution.

## What a PASS still does not mean

It does not establish:

- biological memory equivalence;
- SNpp39/SNpp41 polarity;
- biological current or conductance calibration;
- biological latency;
- predictive inhibition;
- continuous single-process 24/7 execution;
- systematic-type runtime mapping.

Those gates remain independent.

## Execution authority

The workflow is manual (`workflow_dispatch`) and uses only
`ubuntu-latest`. It restores the latest production checkpoint into an isolated
proof directory and never saves that proof state back into the production
cache.

This PR prepares the real proof path. The real execution result is authoritative
only after the workflow itself runs successfully and its compact receipt is
reviewed.
