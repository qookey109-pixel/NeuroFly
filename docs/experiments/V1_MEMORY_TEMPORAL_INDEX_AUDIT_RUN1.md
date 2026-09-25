# V1 Reward Memory Temporal Index Audit — Run 1

## Status

**EXPLORATORY TEMPORAL INDEX AUDIT COMPLETE**

Successful GitHub Actions run: `36095883843`

- artifact id: `10847468546`
- artifact digest: `sha256:947633623b5a8f6071833abf7f04283e6a0f3a7c147183f79a199ce9b90c16ba`
- receipt digest: `573c10a5f52a03fa7a04226979c14594b59eb56da763a150057ff2137289ed72`
- source checkpoint: `b98e621d1132a1cbefe47dfc1b5026e1107e32f6a0c6754ed47d7445c2a57563`

The production checkpoint was unchanged. All preregistration and evidence gates
passed.

## Frozen question

The Stonkfly KC eligibility trace is frozen at **1.0 s** and NeuroFly advances
**50 ms per decision**, so this exploratory run used the preregistered
**20-decision / one-time-constant** history. This interval is not a hard cutoff
for older history.

The study asked whether the prereward history both:

1. matches the KC eligibility carried by reward-modified KC→MBON07 edges; and
2. can re-engage those changed-KC pathways after transient state is cleared.

No learning parameters, seeds, reward event, or replay lag were selected after
seeing the result.

## Reward-time eligibility

Across the four fresh replicates:

- mean changed reward edges: **1490.75**
- mean fraction of changed edges with positive prereward KC trace: **0.997995097138**
- mean changed-edge KC trace: **4.276311382904 Hz**

Per replicate, positive prereward trace fractions were:

- TI1: **0.993319973280**
- TI2: **0.998660415271**
- TI3: **1.000000000000**
- TI4: **1.000000000000**

Therefore the changed reward-memory edges were not an arbitrary set unrelated
to the prereward sensory history. Almost all carried positive KC eligibility at
reward time.

## State-cleared temporal replay

After preserving synaptic memory, clearing transient neural state, freezing
plasticity, and replaying lags `-20 ... 0` without external reinforcement:

- changed-KC sequence activity occurred in **2 / 4** replicates
- MBON07 state difference occurred in **2 / 4**
- MBON07 spike difference occurred in **2 / 4**
- sequence action divergence occurred in **1 / 4**
- reward-event cue action divergence occurred in **0 / 4**

### TI1

- seed: `2903`
- natural reward event index: `21`
- acquisition length: `27` decisions
- changed edges: `1497`
- unique changed presynaptic KCs: `753`
- first changed-KC reactivation: **lag -10**
- first MBON07 state difference: **lag -10**
- sequence MBON07 spike difference: **observed**
- sequence action divergence: **not observed**
- reward cue changed-KC active fraction: `0.403718459495`
- reward cue engaged paired L1 fraction: `0.588636794104`
- reward cue action divergence: **false**

### TI2

- seed: `2909`
- natural reward event index: `52`
- acquisition length: `58` decisions
- changed edges: `1493`
- unique changed presynaptic KCs: `751`
- changed-KC sequence reactivation: **not observed**
- MBON07 state or spike difference: **not observed**
- reward cue engagement: **0**
- reward cue action divergence: **false**

### TI3

- seed: `2917`
- natural reward event index: `42`
- acquisition length: `48` decisions
- changed edges: `1488`
- unique changed presynaptic KCs: `749`
- changed-KC sequence reactivation: **not observed**
- MBON07 state or spike difference: **not observed**
- reward cue engagement: **0**
- reward cue action divergence: **false**

### TI4

- seed: `2927`
- natural reward event index: `27`
- acquisition length: `33` decisions
- changed edges: `1485`
- unique changed presynaptic KCs: `747`
- first changed-KC reactivation: **lag -15**
- first MBON07 state difference: **lag -15**
- sequence MBON07 spike difference: **observed**
- sequence action divergence: **observed**
- divergent lags: `-13, -12, -11, -8`
- at lag `-8`: no-pulse `HOLD`, reward-memory `TURN_RIGHT`
- reward cue changed-KC active fraction: `0.325301204819`
- reward cue engaged paired L1 fraction: `0.438177701044`
- reward cue action divergence: **false**

## Interpretation

The previous single-cue localization result must now be stated more narrowly.

The current evidence chain is:

`reward pulse`
→ persistent KC→MBON07 synaptic difference
→ prereward KC eligibility on almost all changed edges
→ state-cleared 20-step temporal replay re-engages changed KCs in **2 / 4**
→ MBON07 expression in **2 / 4**
→ sequence action divergence in **1 / 4**
→ instantaneous reward-event cue action divergence in **0 / 4**

Thus temporal context can re-express the stored memory in some trajectories,
but the readout is heterogeneous and is not a stable single-cue association.

This run does **not** validate learning, confirm a temporal cue index, establish
causal learned behavior, or authorize behavioral promotion.

## Next preregistered mechanism question

The next study should reconstruct eligibility state directly before changing
decoder, gain, pulse, KC threshold, or MBON weights.

For each fresh trajectory:

1. preserve the original reward-time per-edge / per-KC `rate_kc` eligibility
   vector;
2. state-clear the paired recall branches;
3. replay the frozen sensory history;
4. compare the replayed `rate_kc` vector with the original reward-time vector
   at every lag;
5. preregister a longer **3 tau = 60 decision** history, where history older
   than 3 time constants has only about 5% residual contribution;
6. use the first qualifying natural reward with a complete 60-decision history;
7. do not replace seeds or tune learning parameters after outcome inspection.

This separates three possibilities: the 20-step history is insufficient to
reconstruct eligibility state, the sensory sequence is not reproducible after
state clearing, or expression depends on additional internal temporal context.

## Claim state

The observed exploratory facts may be frozen as true:

- `pre_event_eligibility_supported`
- `temporal_sequence_reengagement_observed`
- `mbon07_expression_observed`
- `sequence_action_divergence_observed`

The following remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `cue_indexing_failure_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
