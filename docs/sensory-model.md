# NeuroFly sensory model

Status: experimental engineering proxy

NeuroFly does **not** claim that the MaleCNS connectome plus these adapters is a complete living fly or a validated reconstruction of Drosophila perception. The goal is narrower: stop giving the agent privileged game-state information and translate the game into sensory signals that are closer to the kinds of inputs a fly nervous system normally receives.

## Visual input — `neurofly-compound-eye-proxy-v1`

The public maze remains a top-down visualization for humans. MaleCNS no longer receives that omniscient map directly.

Before each neural decision NeuroFly converts the maze renderer into a fly-centered wide panorama:

- 300° engineered horizontal field of view with a rear blind sector.
- The panorama is anchored to the fly's current heading.
- Walls are ray-cast as luminance contrast rather than exposed as grid coordinates.
- Near walls occupy more retinal height, so approach creates visual expansion.
- Predators are dark high-contrast silhouettes; approaching predators occupy increasing retinal area (a looming proxy).
- Food is represented only as small blue/green-biased local visual targets. It does not encode a route or desired action.
- Successive frames change as the fly and predators move, allowing retained visual dynamics to receive optic-flow / motion information over time.

The resulting 320×180 RGB sensory frame is passed into the pinned Stonkfly `VisualMemoryBrain`. Stonkfly maps image luminance to identified R1–R6-like inputs and blue/green proxies to mapped R8 inputs in the retained MaleCNS graph. NeuroFly does not invent unmapped photoreceptor neurons.

Telemetry reports the adapter version, field of view, visible predator count, nearest predator bearing/distance, looming proxy, local wall distances, and left/right frame-change magnitudes. These are diagnostics; they are not target actions.

## Olfactory input — `neurofly-virtual-olfaction-v1`

Food and danger remain separate bilateral odor channels:

- Food: ORN_DM1 / Or42b appetitive proxy.
- Danger: ORN_DA2 / Or56a / geosmin-like aversive proxy.
- Left/right intensity depends on relative source position and distance.
- Odor does not provide a solved path or action label.

These mappings are intentionally labeled engineered proxies. Pellets and game enemies do not literally emit those molecules.

## Reinforcement is not a sense

Reward and aversive stimulation remain outcome signals delivered after events. They are kept separate from visual and olfactory inputs so the agent is not told the correct action in advance.

## Current sensory stack

1. Wide-field visual contrast and color proxy.
2. Temporal visual change / optic-flow opportunity through successive retinal frames.
3. Looming geometry from approaching objects.
4. Bilateral appetitive food odor.
5. Bilateral aversive danger odor.
6. Event-based reward / aversive reinforcement after outcomes.

## Strict neural-input boundary

`neurofly-sensory-contract-v0.1` separates fly-accessible neural input from human diagnostics.

Exact coordinates, source locations, metric distances, bearings, targets, paths and other world-truth fields may exist in diagnostics for testing and visualization, but they are forbidden from the machine-readable neural-input payload. Vision continues to reach MaleCNS as an egocentric retinal RGB proxy; olfaction is reduced to bounded bilateral intensity channels before neural stimulation.

See [`SENSORY_CONTRACT_V01.md`](SENSORY_CONTRACT_V01.md) and `src/neurofly/sensory_contract.py`.

## Not yet modeled

The following are candidates for later versions, but NeuroFly should not invent biological neuron mappings without verifying MaleCNS annotations and a defensible transduction model:

- antennal mechanosensation / airflow;
- leg and body proprioception;
- contact mechanosensation;
- gustation on food contact;
- temperature / humidity;
- polarized-light compass signals.

Each future modality should be versioned, separately testable, and clearly marked as biological evidence versus NeuroFly engineering.
