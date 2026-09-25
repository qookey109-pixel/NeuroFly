# V1 Memory Scheduler + Distributed-State Control — Run 1

Status: **COMPLETE / FROZEN**

## Successful run

- run: `36116327415`
- scientific head: `ec3b8fc408cfedef6ac0aeacfd9d9841fd630908`
- artifact: `10856330414`
- artifact SHA-256: `af9823ed48cad96c03692c336cf6a25b675eb3e18a59261343e9e26084e5f8dc`
- receipt SHA-256: `cafe01b55cafba293bd0f9025dbc4fa832de3a2aa643dbbb2f352b633ce34bfb`
- source checkpoint unchanged: `7706cad7228a127b65a668fea2007a72bc514dea5ae7e4bc68b52084ed9ead0d`
- all preregistration and evidence gates: PASS

## Result

### Scheduler equivalence control

`coherent_scheduler_rebuild` was **exactly identical to intact** for all four
fresh trajectories on every terminal per-lag expression endpoint.

This excludes the tested scheduler representation as the positive expression
carrier:

- absolute cursor/time origin
- delayed-event queue ring indexing
- lazy `last` timestamps
- eligibility/modulation timestamps
- `active / active_flag / nactive` bookkeeping

The rebuild preserved physical transient arrays and synaptic memory.

### v/g + adaptation

Clearing `v/g + adaptation` did **not** suppress expression. Aggregate
expression increased, and the otherwise silent SD2 trajectory acquired
expression.

Therefore this pair is not the positive carrier.

### Broad physical transient clear

Jointly clearing:

- `v`
- `g`
- `adaptation`
- `luminance`
- `refractory`
- `queue`
- `queue_count`

strongly reduced neural memory expression relative to intact:

| Endpoint | Intact | Broad clear | Relative change |
|---|---:|---:|---:|
| changed-KC active fraction | 0.256152 | 0.087764 | -65.7% |
| changed-edge L1 engaged | 0.379950 | 0.133538 | -64.9% |
| MBON07 state-difference fraction | 0.750000 | 0.273810 | -63.5% |
| MBON07 spike-difference fraction | 0.202381 | 0.047619 | -76.5% |
| action-divergence fraction | 0.107143 | 0.059524 | -44.4% |

For every trajectory that expressed memory under intact recall, the broad
physical clear reduced upstream KC/edge engagement and MBON07 expression.

The reward-cue action-divergence fraction rose from `0/4` to `2/4`.
That makes the abrupt composite intervention unsuitable as evidence of
stronger cue-specific memory; it is treated as a perturbation effect, not
promotion evidence.

## Mechanistic conclusion

The extra-history expression benefit is **not carried by lazy scheduler
bookkeeping**.

The strongest current evidence is instead for a **joint physical
transient-state dependency**. No already-tested single state class explains
the carry by itself, while the composite physical-state clear sharply reduces
expression.

This does **not** identify a unique carrier. The next clean step is an
interaction decomposition among:

- luminance
- refractory/delayed-event state
- adaptation
- v/g

with scheduler rebuild retained as an equivalence control.

## Governance

Still false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

No production checkpoint, decoder, reward pulse, KC threshold, MBON weight or
learning parameter was changed.
