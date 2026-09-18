# V0.12 Runtime — Forced Crash Recovery Proof

## Purpose

NeuroFly already has a continuous runtime watchdog that can dispatch a new
training runner when the chain stops and no active runner remains.

What was still missing was direct evidence that a real MaleCNS process can make
verified decisions, terminate abnormally before saving newer state, and then be
recovered from the last coordinated checkpoint without that checkpoint having
been partially modified.

This experiment fills that gap.

## Isolation

The workflow restores the latest production checkpoint as a read-only source
and copies both coordinated files into an isolated proof directory:

- brain.npz
- brain.maze.json

The proof never writes its result back into the production cache.

## Forced crash sequence

Each cycle performs:

1. record SHA-256 for the isolated brain and maze checkpoint;
2. start a real MaleCNS crash-worker process;
3. let it produce one or more verified neural decisions;
4. deliberately avoid session.save;
5. flush a compact evidence receipt;
6. exit the process with a non-zero code;
7. hash the checkpoint pair again;
8. require both hashes to be byte-for-byte unchanged;
9. start a distinct recovery process;
10. restore the same persisted checkpoint and run verified MaleCNS training;
11. save a fresh coordinated checkpoint;
12. repeat from the recovered state.

The default contract performs three cycles.

## Why losing unsaved work is correct

The crash-worker deliberately executes neural decisions that are never
checkpointed.

Those decisions are expected to disappear after the crash.

Therefore this experiment does not claim zero data loss. Its authority rule is
more conservative:

The latest successfully persisted coordinated checkpoint remains the only
restart authority.

The proof fails if an abnormal unsaved process modifies either checkpoint file.

## Recovery continuity

The recovery process must:

- be a different operating-system process;
- emit a valid real MaleCNS self-training receipt;
- resume the persisted clear count exactly at batch start;
- keep clear, death and world-tick counters non-decreasing;
- produce a complete new brain plus maze checkpoint pair.

## What a PASS means

A PASS supports the narrow claim that an isolated NeuroFly MaleCNS checkpoint
pair survived repeated forced unsaved process failures and was usable by new
real MaleCNS recovery processes.

## What a PASS does not mean

A PASS does not establish:

- zero data loss;
- preservation of work performed after the last save;
- an actual GitHub watchdog dispatch event;
- 24-hour soak stability;
- continuous single-process uptime;
- immunity to storage corruption;
- production checkpoint mutation.

Those remain separate operational questions.

## Relationship to the watchdog

The existing watchdog answers:

If the bounded runner chain stops, can infrastructure dispatch another runner?

This proof answers:

If the previous real MaleCNS process dies before its next save, is the last
persisted coordinated state still intact and recoverable?

Together they cover different parts of the long-running runtime model.
