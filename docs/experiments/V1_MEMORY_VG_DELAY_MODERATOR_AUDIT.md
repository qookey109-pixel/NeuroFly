# V1 Reward Memory v/g + Delay Moderator Audit

Status: **PREREGISTERED EXPLORATORY DISCOVERY**

## Why this study exists

Cross-subsystem localization (#159) found `v/g + refractory/delay` as the
only tested cross-pair with 4/4 suppression on the three primary neural
expression endpoints.

Fresh replication (#160) did **not** reproduce history-general robustness:

- VR1: suppression
- VR2: suppression
- VR3: suppression
- VR4: reversal on all three primary endpoints

Therefore the next question is not `v` versus `g`.

The next question is:

**Which pre-intervention state or trajectory features distinguish histories in
which the same intervention suppresses expression from histories in which it
does not?**

## Fresh outcome-blind cohort

A frozen pool of 30 candidate seeds is scanned in exact order.

The first **8** candidates with both unique pre-event checkpoint SHA-256 and
unique stable sensory-sequence SHA-256 are selected before any effect label is
computed.

No seed replacement is allowed.

## Shared protocol

Every selected history uses:

- paired reward/no-pulse synaptic memory;
- five reinforcement-free delay decisions;
- exact prefix `-60...-21`;
- boundary after lag -21;
- exact terminal `-20...0`;
- frozen learning;
- zero recall reinforcement.

Only two terminal conditions are required:

1. `intact`
2. `clear_vg_delay`: clear `v, g, refractory, queue, queue_count`

## Moderator features

Features are measured **after the exact prefix and before the boundary
intervention**.

Frozen physical fields:

- `v`
- `g`
- `adaptation`
- `luminance`
- `refractory`
- `queue_count`
- `nactive`

For paired none/true branches, report frozen descriptive summaries including
mean, standard deviation, 95th percentile absolute magnitude, maximum absolute
magnitude and nonzero fraction where meaningful.

Also report paired mean / absolute branch difference summaries.

Frozen prefix-expression features include:

- mean changed-KC active fraction
- mean changed-edge L1 engagement
- MBON07 state-difference fraction
- MBON07 spike-difference fraction
- action-divergence fraction
- the same key neural measures at lag -21

Trajectory-level features include event index and changed reward-edge count.

## Effect labels

After the selection manifest and pre-intervention features are frozen:

- **suppression**: `clear_vg_delay < intact` on all three primary endpoints
- **reversal**: `clear_vg_delay > intact` on all three
- **mixed**: anything else

## Analysis boundary

This is explicitly **exploratory discovery**.

All frozen features are reported. If both suppression and non-suppression
groups exist, standardized mean differences may be reported descriptively.

No p-value threshold, feature-selection threshold, causal interpretation or
promotion is allowed.

Any moderator hypothesis discovered here must be frozen and tested in a new
outcome-blind cohort before it can be called confirmed.

## Governance

No model parameter or production-checkpoint mutation.

All learning, carrier, causality, moderator-confirmation and behavioral
promotion locks remain false.
