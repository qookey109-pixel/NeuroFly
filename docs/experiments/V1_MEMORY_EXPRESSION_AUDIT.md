# V1 Reward Memory Expression Audit

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Origin

Reward-memory recall v0.2 showed a persistent compartment-local paired synaptic
difference but no detected state-cleared recall difference in KC total spikes,
DNp20 readout, gate spikes, total spikes, or action.

This study does not change the learning rule. It localizes where the stored
difference stops being expressed.

## Question

Does the stored KC→MBON07 difference fail because:

1. recall-active KCs do not presynaptically engage the changed edges; or
2. changed edges are engaged but MBON07 does not change; or
3. MBON07 changes but the current DNp20/DNpe017 decoder does not receive/express
   that difference?

## Frozen design

Four new seeds: 2801, 2803, 2819, 2833.

The event acquisition, paired pulse/no-pulse branches, five no-reinforcement
delay decisions, state-clearing reset, frozen recall plasticity and exact-cue
recall all follow reward-recall v0.2.

No model parameter is modified.

## Measurements

For the reward compartment only:

- number of edges with a nonzero paired post-delay efficacy difference;
- fraction of those edges whose presynaptic KC spikes during recall;
- fraction of paired synaptic L1 difference lying on recall-active presynaptic
  edges;
- fraction of unique changed presynaptic KCs active during recall;
- MBON07 spike-count delta;
- MBON07 post-recall membrane-potential and conductance deltas;
- DNp20 and DNpe017 post-recall membrane-potential deltas;
- decoded action divergence.

Membrane/conductance measurements are internal model-state diagnostics, not
biological voltage calibration claims.

## Boundary

There is no PASS threshold and no behavioral promotion.

The study can localize the current implementation bottleneck. It cannot make
`learning_validated=true` or authorize a replacement confirmatory study.
