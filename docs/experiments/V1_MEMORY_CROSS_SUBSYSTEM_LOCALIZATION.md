# V1 Memory Cross-Subsystem Localization

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Motivation

The diversity-recovery study replicated a non-additive joint physical-state
dependency across four genuinely distinct neural histories:

- clearing `v/g + adaptation` alone preserves expression;
- clearing `luminance + refractory/delay` alone preserves expression;
- clearing both together sharply suppresses KC/edge/MBON07 expression.

The next efficient question is which **minimal cross-subsystem pair** carries
most of that redundancy.

## Scheduler control

The coherent scheduler rebuild is retired from this round to reduce compute.
It has already been exact endpoint-equivalent to intact repeatedly, including
the latest neural-diverse study.

This retirement does not open a scheduler claim; it only avoids repeating an
already stable equivalence control.

## Outcome-blind neural diversity

A fresh frozen candidate pool is scanned in exact order:

`5209, 5227, 5231, 5233, 5237, 5261, 5273, 5279, 5281, 5297, 5303, 5309, 5323, 5333, 5347, 5351, 5381, 5387, 5393, 5399`

The first four candidates with both unique pre-event checkpoint SHA-256 and
unique stable sensory-sequence SHA-256 are frozen before any expression
condition is evaluated.

The stable sensory digest removes only the preregistered volatile wall-clock
keys already used successfully in #158.

## Conditions

All interventions occur after source lag -21 and before lag -20.

1. `intact`
2. `clear_vg_luminance`: clear `v, g, luminance`
3. `clear_vg_delay`: clear `v, g, refractory, queue, queue_count`
4. `clear_adaptation_luminance`: clear `adaptation, luminance`
5. `clear_adaptation_delay`: clear `adaptation, refractory, queue, queue_count`
6. `clear_broad_physical_transient`: full A+B reference

Every condition uses identical paired synaptic memory, exact prefix
`-60...-21`, exact terminal `-20...0`, frozen learning and zero recall
reinforcement.

## Analysis

For every endpoint report:

- condition minus intact;
- broad clear minus condition.

The key descriptive question is which cross-pair moves neural expression
closest to the broad-clear phenotype.

No formal significance threshold or post-hoc pair selection is allowed.

## Governance

This remains mechanistic localization only.

No decoder, reward pulse, KC threshold, MBON weight, learning parameter or
production checkpoint changes.

All learning / carrier / causal / promotion locks remain false.
