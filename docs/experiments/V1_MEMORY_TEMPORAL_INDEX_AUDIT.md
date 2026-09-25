# V1 Reward Memory Temporal Index Audit

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

Memory-expression run 1 found a persistent paired reward-memory difference on
1,522 KC→MBON07 edges from 768 presynaptic KCs, but the isolated state-cleared
reward-event frame activated none of those changed KCs.

The frozen Stonkfly rule uses a **1.0 second KC trace**. NeuroFly advances
**50 ms per decision**, so one model trace time constant equals **20 decisions**.

That fixes the temporal window used here; it is not selected after looking at
the result.

## Question

Does the one-time-constant prereward history identify and re-engage the
presynaptic KC ensemble that carries the stored reward-memory difference?

## Event acquisition

Four new seeds are frozen:

- TI1 / 2903
- TI2 / 2909
- TI3 / 2917
- TI4 / 2927

For each seed, acquisition starts at decision zero. The target event is the
**first natural reward at or after decision index 20**, so a complete 20-step
prereward history is always available.

The acquisition then records exactly five later decisions and stops.

Maximum acquisition is 300 decisions. A seed with no qualifying reward is
invalid and is not replaced.

Earlier natural rewards during the warmup are recorded as environment events
but are never delivered as external reinforcement to the frozen trajectory
driver or pre-event history reconstruction.

## Two measurements

### 1. Eligibility state at reward time

After reconstructing the paired pre-event checkpoint, the audit reads the
frozen model's per-edge `rate_kc` trace and asks what fraction of the eventual
changed reward edges already carry positive KC eligibility at reward time.

This directly tests the temporal state used by the learning rule.

### 2. State-cleared sequence recall

After the paired reward/no-pulse branches and the same five
reinforcement-free delay decisions:

1. preserve the branch synaptic memory;
2. clear transient neural state;
3. freeze plasticity;
4. replay exactly the 20 recorded prereward frames/contexts in order;
5. replay the exact reward-event frame/context;
6. deliver no external reinforcement anywhere in recall.

For every lag `-20 ... 0`, the audit reports:

- fraction of changed presynaptic KCs that spike;
- fraction of changed-edge paired L1 carried on edges with an active
  presynaptic KC;
- MBON07 spike / membrane / conductance paired differences;
- DNp20/DNpe017 state differences;
- action divergence.

## Boundary

The 1-second interval is one frozen model time constant, not a biological
hard cutoff. A negative result does not prove that older history is irrelevant.

No learning or behavioral claim is unlocked by this exploratory localization
study.
