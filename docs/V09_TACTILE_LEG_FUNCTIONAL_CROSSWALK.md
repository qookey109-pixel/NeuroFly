# V0.9 Tactile Leg Functional Crosswalk

Status: evidence-backed read-only crosswalk. No tactile current and no runtime contact transduction are enabled by this stage.

## Purpose

The V0.9 annotation audit established that the pinned MaleCNS graph contains 2,558 exact `mechanosensory_tactile` neurons, but that population spans leg, notum, wing, and generic mechanosensory bristle annotations. It is too broad to stimulate safely as a single contact channel.

This stage therefore asks a narrower question:

> Which exact retained SNta types have direct external anatomical evidence linking that type to an adult leg nerve, while remaining unambiguous inside the pinned MaleCNS curator annotations?

## Candidate v0.1 and why it was rejected

The first candidate crosswalk contained eight exact type labels:

`SNta20`, `SNta26`, `SNta27`, `SNta28`, `SNta30`, `SNta34`, `SNta37`, `SNta42`.

Prepared MaleCNS audit run `34796509815` rejected that candidate even though it selected 719 exact tactile rows, because two type names also occurred in retained rows outside the exact tactile class:

- `SNta30`: 11 rows with `class=unknown_sensory`, `subclass=mechanosensory bristle`, `superclass=vnc_sensory`
- `SNta42`: 2 rows with `class=unknown_sensory`, `subclass=mechanosensory bristle`, `superclass=vnc_sensory`

The class gate was **not** relaxed. Those two types were removed from the next candidate instead. The rejected v0.1 ledger is preserved at:

`data/tactile_leg_functional_crosswalk_v01.json`

## Conservative crosswalk v0.2

Six exact single type labels remain as **leg-associated external-touch candidates**:

- `SNta20`
- `SNta26`
- `SNta27`
- `SNta28`
- `SNta34`
- `SNta37`

Each mapping has explicit Virtual Fly Brain / MaleCNS anatomical evidence that at least one record of that exact type fasciculates with an adult mesothoracic or metathoracic leg nerve. `SNta27` also has a direct curator `subclass=leg` record.

The active machine-readable evidence ledger is:

`data/tactile_leg_functional_crosswalk_v02.json`

## Accepted curator subclasses

A mapped exact type may be retained only when its pinned MaleCNS row is itself `class=mechanosensory_tactile` and its subclass is one of:

- `leg`
- `mechanosensory bristle`

Any same-name row outside `mechanosensory_tactile` remains a hard failure. If any mapped exact type appears in `notum`, `wing`, or another unexpected subclass, the prepared audit also fails closed. This protects against extending type-level leg-nerve evidence into a different or unresolved sensory population.

## Ambiguous labels remain unresolved

Combined or uncertain type labels are never split. Examples include:

- `SNta20,SNta29`
- `SNta27,SNta28`
- `SNta28,SNta29`
- `SNta28,SNta40`
- `SNta28,SNta44`
- `SNta31,SNta34`
- `SNta19,SNta37`
- `SNtaxx`
- `SNxxxx`

Even when such a label contains one approved token, the entire row remains unresolved.

## Evidence tiers

The audit reports selected neurons in two evidence tiers:

1. `curator_leg_plus_external_nerve`
   - exact approved SNta type
   - curator subclass `leg`
   - direct external leg-nerve evidence
2. `external_leg_nerve_plus_bristle_class`
   - exact approved SNta type
   - curator subclass `mechanosensory bristle`
   - direct external leg-nerve evidence

Both tiers remain discovery candidates only. Neither authorizes neural stimulation.

## Hard gates

A PASS for v0.2 requires:

- all 6 exact crosswalk types are present in the pinned graph;
- selected rows are exactly `mechanosensory_tactile`;
- no mapped type has a same-name retained row outside the tactile class;
- no mapped type appears in a disallowed subclass;
- combined labels remain unselected;
- exact selected population is 590 neurons for the pinned MaleCNS/Stonkfly baseline;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`.

## Runtime boundary

This crosswalk does not yet define what a wall collision, floor contact, food touch, enemy touch, or leg loading event should become neurally.

A future contact transducer must expose only a bounded fly-relative physical contact signal. It must not expose engine truth such as object ID, wall coordinates, exact collision normals, target labels, route information, reward, or desired action.

Because NeuroFly currently uses a compact game-body proxy rather than a six-leg biomechanical model, the first runtime tactile channel should be treated as an **engineering external-touch proxy** routed only after separate prepared-MaleCNS current calibration. It must not be described as a complete reconstruction of leg-bristle physiology.

## Proprioception remains separate

This PR intentionally does not map FeCO club/claw/hook populations into runtime. Proprioception needs a receptor-accessible body/joint-state model first. Raw game velocity, heading, or world displacement are privileged simulation variables and must not be injected as if they were biological proprioception.

## No changes to existing senses

This stage does not modify:

- compound-eye vision;
- olfaction;
- default-on JO-C / JO-E airflow mechanosensation;
- contact-only gustation;
- reward or aversive reinforcement;
- decoder policy;
- learning/plasticity policy.
