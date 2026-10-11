# Stage 2 odor-gain A/B evidence gate

## Context (2026-10-11)

The production-trained fly remains in Stage 2. The already-shipped
`danger-orn-stage2-ab.yml` tested isolated gains `1.6 / 2.4 / 3.2`,
but only listened to `push` on `main` or manual `workflow_dispatch`.

That meant a PR could receive all ordinary unit/integration test green
checks, get merged, and still have **no reviewed live MaleCNS maze A/B
behavioral receipt**. This PR changes the *evidence collection timing*.

## New gate

The same read-only A/B workflow now also runs for relevant PR updates, using
the actual PR candidate code rather than unconditionally checking out
`main`. This enables review of the trial's run status, diagnostics, and
downloadable receipt before any production code promotion.

The same full experiment remains unchanged:
- Source production `brain.npz`, `brain.maze.json` and
  `brain.decoder.json` restored as a read-only checkpoint source.
- Three independent arm copies, each starting at Stage 2 from that source.
- Danger sensory gain 1.6 / 2.4 / 3.2, 600 decisions per arm.
- No direct action override; neural actions remain sole controller.
- Independent wall-clock predator exposure audited. Each arm records predator
  world ticks and applied/discarded neural decisions. Comparison flags are
  suppressed for large exposure mismatch.
- No mutation of production checkpoint, no live telemetry publication, no
  deployment of candidate neural code, no promotion on a favorable signal.
- Full reports remain short-lived GitHub Actions artifacts.

The PR event uses only `contents: read`; no repository write token, secrets
or external deployment privileges are required. Experiment artifacts are
not substitutes for independent repeats or Stage 2 clears.

## Reviewer acceptance

1. Verify the PR-triggered **NeuroFly Stage 2 Danger ORN Maze A-B** workflow
   ran on the reviewed head and completed successfully.
2. Download and inspect `report.json` plus the three
   `behavior-summary.json` artifacts.
3. Confirm source SHA equality and `source_checkpoint_unchanged=true`.
4. Check `world_tick_delta`, applied/ discarded decisions, and
   `exposure_comparable` before looking at behavioral deltas.
5. Avoid interpreting a lone exploratory advantage as verified Stage 2
   improvement. Require repeated, controlled evidence for production change.

**A CI pass alone never means a successful Stage 2 clear.**
