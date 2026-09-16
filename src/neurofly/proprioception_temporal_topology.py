from __future__ import annotations

import copy
from typing import Any

from .proprioception_temporal_analysis import (
    PROPRIOCEPTION_TEMPORAL_ANALYSIS_TIMEBASE,
    _validated_samples,
)
from .proprioception_temporal_observability import PROPRIOCEPTION_TEMPORAL_SOURCE


PROPRIOCEPTION_HOOK_TOPOLOGY_SCHEMA = (
    "neurofly-proprioception-hook-temporal-topology-v0.1"
)

_HOOK_EXTENSION = "hook_extension"
_HOOK_FLEXION = "hook_flexion"


def _validate_engineering_hook_invariants(samples: list[dict[str, Any]]) -> None:
    """Fail closed before interpreting directional event topology.

    The reviewed engineering receptor contract requires extension/flexion to be
    mutually exclusive and club motion to cover the directional motion
    magnitude. Temporal topology is not meaningful when either invariant is
    violated, so this layer rejects the history instead of inventing a repair.
    """

    for sample in samples:
        channels = sample["channels"]
        extension = float(channels[_HOOK_EXTENSION])
        flexion = float(channels[_HOOK_FLEXION])
        club_motion = float(channels["club_motion"])
        if extension > 0.0 and flexion > 0.0:
            raise ValueError(
                "Temporal hook topology requires mutually exclusive extension/flexion"
            )
        if club_motion + 1e-12 < max(extension, flexion):
            raise ValueError(
                "Temporal hook topology requires club motion to cover hook magnitude"
            )


def _direction_state(sample: dict[str, Any]) -> str | None:
    channels = sample["channels"]
    if float(channels[_HOOK_EXTENSION]) > 0.0:
        return _HOOK_EXTENSION
    if float(channels[_HOOK_FLEXION]) > 0.0:
        return _HOOK_FLEXION
    return None


def _directional_events(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for index, sample in enumerate(samples):
        sequence = int(sample["sequence"])
        direction = _direction_state(sample)
        if direction is None:
            current = None
            continue

        level = float(sample["channels"][direction])
        if current is not None and current["direction"] == direction:
            current["observed_end_sequence"] = sequence
            current["observed_duration_decisions"] = (
                int(current["observed_end_sequence"])
                - int(current["observed_start_sequence"])
                + 1
            )
            current["peak_level"] = max(float(current["peak_level"]), level)
            continue

        current = {
            "direction": direction,
            "observed_start_sequence": sequence,
            "observed_end_sequence": sequence,
            "observed_duration_decisions": 1,
            "peak_level": level,
            "left_censored": index == 0,
            "right_censored": False,
        }
        events.append(current)

    if samples and _direction_state(samples[-1]) is not None and events:
        events[-1]["right_censored"] = True
    return events


def _event_transitions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for previous, current in zip(events, events[1:]):
        gap = (
            int(current["observed_start_sequence"])
            - int(previous["observed_end_sequence"])
            - 1
        )
        if gap < 0:
            raise ValueError("Directional events must not overlap")
        alternating = previous["direction"] != current["direction"]
        transitions.append(
            {
                "from_direction": previous["direction"],
                "to_direction": current["direction"],
                "from_end_sequence": int(previous["observed_end_sequence"]),
                "to_start_sequence": int(current["observed_start_sequence"]),
                "idle_gap_decisions": gap,
                "alternating": alternating,
                "direct_reversal": alternating and gap == 0,
                "reversal_after_idle": alternating and gap > 0,
                "same_direction_reentry": (not alternating) and gap > 0,
            }
        )
    return transitions


def analyze_proprioception_hook_temporal_topology(
    history: dict[str, Any],
) -> dict[str, Any]:
    """Describe hook-direction event topology using decision indices only.

    The input is the already-reviewed, human-only receptor history. No action,
    reward, world state, private body state, wall-clock time, systematic neuron
    identity, or SNpp mapping is accepted by that history contract.
    """

    samples = _validated_samples(copy.deepcopy(history))
    _validate_engineering_hook_invariants(samples)

    events = _directional_events(samples)
    transitions = _event_transitions(events)
    idle_samples = sum(_direction_state(sample) is None for sample in samples)
    directional_samples = len(samples) - idle_samples

    first_sequence = int(samples[0]["sequence"]) if samples else None
    last_sequence = int(samples[-1]["sequence"]) if samples else None
    gaps = [int(transition["idle_gap_decisions"]) for transition in transitions]

    return {
        "schema": PROPRIOCEPTION_HOOK_TOPOLOGY_SCHEMA,
        "source": PROPRIOCEPTION_TEMPORAL_SOURCE,
        "human_only": True,
        "timebase": PROPRIOCEPTION_TEMPORAL_ANALYSIS_TIMEBASE,
        "sample_count": len(samples),
        "first_retained_sequence": first_sequence,
        "last_retained_sequence": last_sequence,
        "window_left_censoring_possible": bool(samples and first_sequence != 1),
        "engineering_mutual_exclusion_verified": True,
        "engineering_club_motion_coverage_verified": True,
        "directional_active_sample_count": directional_samples,
        "idle_sample_count": idle_samples,
        "directional_event_count": len(events),
        "directional_events": events,
        "event_transition_count": len(transitions),
        "event_transitions": transitions,
        "alternating_event_transition_count": sum(
            bool(transition["alternating"]) for transition in transitions
        ),
        "direct_reversal_count": sum(
            bool(transition["direct_reversal"]) for transition in transitions
        ),
        "reversal_after_idle_count": sum(
            bool(transition["reversal_after_idle"]) for transition in transitions
        ),
        "same_direction_reentry_count": sum(
            bool(transition["same_direction_reentry"]) for transition in transitions
        ),
        "observed_idle_gap_decisions_total": sum(gaps),
        "observed_idle_gap_decisions_max": max(gaps, default=0),
        "milliseconds_inferred": False,
        "step_cycle_phase_resolved": False,
        "inhibitory_lead_time_resolved": False,
        "biological_identity_resolved": False,
        "motor_command_used": False,
        "reward_used": False,
        "world_state_used": False,
        "private_body_state_used": False,
        "systematic_type_mapping_exposed": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_eligible": False,
        "analysis_persistence_enabled": False,
    }
