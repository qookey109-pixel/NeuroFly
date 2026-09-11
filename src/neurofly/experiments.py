from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Experiment:
    slug: str
    name: str
    summary: str
    side_effects: bool = False


EXPERIMENTS: tuple[Experiment, ...] = (
    Experiment(
        "light-chase",
        "Light Chase",
        "Drive a tiny agent from visual/light input and decode orientation-like output.",
    ),
    Experiment(
        "neuro-maze",
        "Neuro Maze",
        "Map neural output to left/right/forward movement inside a maze.",
    ),
    Experiment(
        "brain-scope",
        "Brain Scope",
        "Visualize population activity while changing controlled stimuli.",
    ),
    Experiment(
        "connectome-arcade",
        "Connectome Arcade",
        "Use a common neural adapter interface to control small games.",
    ),
    Experiment(
        "dopamine-lab",
        "Dopamine Lab",
        "Compare engineered reinforcement schedules and plasticity controls.",
    ),
    Experiment(
        "sensory-swap",
        "Sensory Swap",
        "Compare responses to price charts, geometry, motion and game frames.",
    ),
    Experiment(
        "stonkfly-replay",
        "Stonkfly Replay",
        "Run the upstream trading experiment as an isolated paper/simulation adapter.",
    ),
)


def list_experiments() -> tuple[Experiment, ...]:
    return EXPERIMENTS
