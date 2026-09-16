# V0.11 Proprioception Temporal Event Visualization

Status: **REVIEW_REQUIRED / human-only browser-derived visualization**

This stacked stage visualizes the descriptive event semantics introduced by the preceding temporal event-analysis stage without widening the production public-state surface and without creating a biological timing or systematic-type binding.

## Stack authority

Base: `feature/v0.11-proprioception-temporal-event-analysis` at reviewed head `2f17fb4edb65fdb5d82a534aa73a6e3822844576` (Draft PR #71).

Inherited scientific boundaries remain unchanged:

- engineering model: `neurofly-feco-motion-proxy-v0.1`;
- engineering encoding: `virtual-joint-motion-only-proxy`;
- public temporal source: `verified-neural-handoff-receptor-domain`;
- bounded history capacity: at most 36 samples;
- direct SNpp39/SNpp41 flexion/extension type-level crosswalk remains unresolved;
- `SNpp39 ≈ extension-sensitive hook` and `SNpp41 ≈ flexion-sensitive hook` remain `PHYSIOLOGY_SUPPORTED_INFERENCE` only;
- no proprioceptive current, calibration, stimulation, or runtime systematic-type routing is authorized.

## Publication boundary

This stage does **not** add `human_diagnostics.proprioception_temporal_analysis` to the production public-state allowlist.

The browser continues to consume only the already-reviewed public raw history:

`human_diagnostics.proprioception_temporal`

The descriptive event summary is recomputed locally in `site/all-clear-history.js`. Therefore the production publisher and relay do not gain another diagnostic field and the visualization remains reproducible from the existing public evidence surface.

## Fail-closed input contract

Before any event is derived, the browser validates the same bounded temporal contract used by the reviewed Python analyzer:

- exact temporal-history field allowlist;
- exact sample field allowlist;
- schema `neurofly-proprioception-temporal-observability-v0.1`;
- source `verified-neural-handoff-receptor-domain`;
- `human_only=true`;
- capacity in `1..36`;
- `sample_count == samples.length <= capacity`;
- positive contiguous sequence identifiers inside the retained window;
- exact four engineering receptor channels;
- finite receptor levels in `[0,1]`;
- persistence, current, stimulation, runtime transduction, systematic-type mapping, and neural-payload locks remain closed.

An unexpected field is not displayed or used as a feature; the event visualization fails closed.

## Event semantics

For each engineering receptor channel independently, a retained sample is descriptively active when:

`level > 0`

A contiguous retained run of active samples is one observed event. The browser derives only:

- observed start sequence;
- observed end sequence;
- observed duration in decision indices;
- peak receptor level;
- left-censoring flag;
- right-censoring flag;
- active-sample count;
- rising transitions visible inside the window;
- falling transitions visible inside the window;
- observed event count.

The displayed window also reports whether left-window censoring is possible when the first retained sequence is no longer sequence 1.

## Timebase boundary

The only supported timebase is:

`decision-index-only`

The UI explicitly does not resolve:

- biological milliseconds;
- step-cycle phase;
- 9A inhibitory lead time.

A duration such as `3 decisions` means only three successive retained verified neural handoffs. It must not be converted to milliseconds or treated as a biological latency.

## Privileged-state exclusion

The browser event derivation does not consume:

- action or motor command;
- reward;
- world state;
- private body state;
- systematic neuron identity;
- SNpp39/SNpp41 polarity labels.

The derived summary is human-only observability and never becomes neural input.

## UI placement

The proprioception panel now remains separated into four planes:

1. **LIVE RECEPTOR INPUT** — latest reviewed receptor-domain handoff;
2. **RECENT RECEPTOR HISTORY** — bounded raw reviewed history;
3. **TEMPORAL EVENT ANALYSIS** — browser-local descriptive decision-index summary;
4. **CONTROL PLANE** — unresolved systematic-type candidates and locks.

This separation is deliberate: temporal structure in an engineering receptor proxy is not evidence for exact MaleCNS systematic-type identity.

## Regression gates

Tests require that:

- the browser analyzer validates exact reviewed history/sample fields;
- event activity is defined only by receptor `level > 0`;
- left/right censoring and within-window rise/fall transitions are preserved;
- millisecond, phase, and 9A lead-time fields stay unresolved;
- the analyzer reads raw `proprioception_temporal` and not a newly published analysis field;
- the derivation body contains no reward, motor-command, world-state, private-body, systematic-type, SNpp39, or SNpp41 feature;
- systematic-type/current/neural-payload safety text remains visible.

## Non-authorization

This stage does not authorize:

- binding `hook_extension` or `hook_flexion` to SNpp39/SNpp41;
- current injection or calibration;
- stimulation;
- predictive inhibition runtime gating;
- biological phase or millisecond kernels;
- public-state allowlist expansion;
- temporal-history persistence;
- merging the science stack.

Do not merge automatically.
