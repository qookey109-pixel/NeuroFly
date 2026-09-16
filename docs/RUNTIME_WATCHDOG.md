# NeuroFly Continuous Runtime Watchdog

Status: infrastructure recovery design; no scientific model or sensory semantics change.

## Problem

The bounded GitHub Actions curriculum runner safely persists the MaleCNS checkpoint after a successful neural run, then tries to dispatch the next free runner. A failure in that final dispatch step can stop the chain even though training, checkpoint persistence, site-state generation, and evidence publication already succeeded.

## Recovery design

`NeuroFly Runtime Watchdog` runs every 15 minutes from the default branch and can also be triggered manually.

It reads `config/neurofly_continuous_runtime.json` from `main` and exits without starting anything when `enabled=false`.

When continuous runtime is enabled, it queries recent runs of `.github/workflows/full-malecns-free.yml` and:

1. does nothing if any run is queued or active;
2. waits through a three-minute visibility cooldown immediately after the latest run completes so a successful handoff has time to appear in the Actions API;
3. dispatches one new `main` runner only when no active runner exists and the cooldown has elapsed;
4. retries dispatch up to three times; if all retries fail, the next scheduled watchdog pass tries again.

The training workflow's own final handoff also retries three times. A handoff failure is now non-fatal after the checkpoint has been saved, so a successful neural run is not misclassified as failed merely because the next-run dispatch endpoint was temporarily unavailable.

## Duplicate-run protection

The watchdog checks the target workflow queue before recovery. The target curriculum workflow also retains its existing concurrency group, so two MaleCNS jobs cannot execute concurrently. The watchdog has its own concurrency group to prevent overlapping watchdog executions.

## Authority and cost boundary

- authority branch: `main`
- runner: `ubuntu-latest`
- paid resources: forbidden by the existing runtime policy
- checkpoint persistence remains the runtime authority
- the watchdog does not modify the brain, curriculum, reward, sensory inputs, scientific evidence, or checkpoint contents

## Operational result after merge

The intended state machine is:

`train -> save checkpoint -> self-dispatch next runner`

If the self-dispatch fails:

`persisted checkpoint -> watchdog sees no active runner -> recovery dispatch -> restore checkpoint -> continue training`

No automatic merge is authorized by this document.
