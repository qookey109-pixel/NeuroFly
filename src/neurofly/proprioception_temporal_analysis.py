from __future__ import annotations

import copy
import math
from typing import Any

from .proprioception import PROPRIOCEPTION_ENCODING, PROPRIOCEPTION_MODEL
from .proprioception_temporal_observability import (
    MAX_PROPRIOCEPTION_HISTORY_CAPACITY,
    PROPRIOCEPTION_TEMPORAL_SCHEMA,
    PROPRIOCEPTION_TEMPORAL_SOURCE,
)


PROPRIOCEPTION_TEMPORAL_ANALYSIS_SCHEMA = (
    "neurofly-proprioception-temporal-event-analysis-v0.1"
)
PROPRIOCEPTION_TEMPORAL_ANALYSIS_TIMEBASE = "decision-index-only"

_CHANNEL_NAMES = (
    "hook_extension",
    "hook_flexion",
    "club_motion",
    "club_vibration",
)

_EXPECTED_HISTORY_KEYS = {
    "schema",
    "source",
    "human_only",
    "capacity",
    "sample_count",
    "samples",
    "history_persistence_enabled",
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "neural_payload_eligible",
}

_EXPECTED_SAMPLE_KEYS = {
    "sequence",
    "source",
    "model",
    "encoding",
    "channels",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "neural_payload_eligible",
}


def _validated_samples(history: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(history, dict) or set(history) != _EXPECTED_HISTORY_KEYS:
        raise ValueError("Unexpected temporal history fields")
    if history.get("schema") != PROPRIOCEPTION_TEMPORAL_SCHEMA:
        raise ValueError("Unexpected temporal history schema")
    if history.get("source") != PROPRIOCEPTION_TEMPORAL_SOURCE:
        raise ValueError("Unexpected temporal history source")
    if history.get("human_only") is not True:
        raise ValueError("Temporal history must remain human-only")

    capacity = history.get("capacity")
    sample_count = history.get("sample_count")
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("Temporal history capacity must be an integer")
    if not 1 <= capacity <= MAX_PROPRIOCEPTION_HISTORY_CAPACITY:
        raise ValueError("Temporal history capacity exceeds the reviewed bound")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("Temporal history sample count must be an integer")

    for lock in (
        "history_persistence_enabled",
        "systematic_type_mapping_exposed",
        "current_calibration_authorized",
        "stimulation_enabled",
        "runtime_transduction_enabled",
        "neural_payload_eligible",
    ):
        if history.get(lock) is not False:
            raise ValueError(f"Temporal history lock opened: {lock}")

    samples = history.get("samples")
    if not isinstance(samples, list):
        raise ValueError("Temporal history samples must be a list")
    if sample_count != len(samples) or sample_count > capacity:
        raise ValueError("Temporal history count/capacity mismatch")

    previous_sequence: int | None = None
    validated: list[dict[str, Any]] = []
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != _EXPECTED_SAMPLE_KEYS:
            raise ValueError("Unexpected temporal sample fields")
        if sample.get("source") != PROPRIOCEPTION_TEMPORAL_SOURCE:
            raise ValueError("Unexpected temporal sample source")
        if sample.get("model") != PROPRIOCEPTION_MODEL:
            raise ValueError("Unexpected temporal sample model")
        if sample.get("encoding") != PROPRIOCEPTION_ENCODING:
            raise ValueError("Unexpected temporal sample encoding")
        for lock in (
            "stimulation_enabled",
            "runtime_transduction_enabled",
            "systematic_type_mapping_exposed",
            "current_calibration_authorized",
            "neural_payload_eligible",
        ):
            if sample.get(lock) is not False:
                raise ValueError(f"Temporal sample lock opened: {lock}")

        sequence = sample.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise ValueError("Temporal sample sequence must be a positive integer")
        if previous_sequence is not None and sequence != previous_sequence + 1:
            raise ValueError("Temporal sample sequences must be contiguous")
        previous_sequence = sequence

        channels = sample.get("channels")
        if not isinstance(channels, dict) or set(channels) != set(_CHANNEL_NAMES):
            raise ValueError("Unexpected temporal receptor channel set")
        frozen_channels: dict[str, float] = {}
        for channel in _CHANNEL_NAMES:
            value = channels.get(channel)
            if isinstance(value, bool):
                raise ValueError("Temporal receptor level must be numeric")
            try:
                level = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("Temporal receptor level must be numeric") from exc
            if not math.isfinite(level) or not 0.0 <= level <= 1.0:
                raise ValueError("Temporal receptor level must stay within [0,1]")
            frozen_channels[channel] = level

        validated.append(
            {
                "sequence": sequence,
                "channels": frozen_channels,
            }
        )
    return validated


def _channel_analysis(
    samples: list[dict[str, Any]],
    channel: str,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    rising_transitions = 0
    falling_transitions = 0
    active_samples = 0
    previous_active: bool | None = None
    current: dict[str, Any] | None = None

    for index, sample in enumerate(samples):
        sequence = int(sample["sequence"])
        level = float(sample["channels"][channel])
        active = level > 0.0
        if active:
            active_samples += 1

        if active and previous_active is not True:
            if previous_active is False:
                rising_transitions += 1
            current = {
                "observed_start_sequence": sequence,
                "observed_end_sequence": sequence,
                "observed_duration_decisions": 1,
                "peak_level": level,
                "left_censored": index == 0,
                "right_censored": False,
            }
            events.append(current)
        elif active and current is not None:
            current["observed_end_sequence"] = sequence
            current["observed_duration_decisions"] = (
                int(current["observed_end_sequence"])
                - int(current["observed_start_sequence"])
                + 1
            )
            current["peak_level"] = max(float(current["peak_level"]), level)

        if not active and previous_active is True:
            falling_transitions += 1
            current = None

        previous_active = active

    if samples and previous_active is True and events:
        events[-1]["right_censored"] = True

    return {
        "active_sample_count": active_samples,
        "rising_transition_count_within_window": rising_transitions,
        "falling_transition_count_within_window": falling_transitions,
        "event_count_observed": len(events),
        "events": events,
    }


def analyze_proprioception_temporal_history(
    history: dict[str, Any],
) -> dict[str, Any]:
    """Derive human-only event summaries from the reviewed receptor history.

    Time is represented only by retained neural-handoff sequence index. This
    function intentionally does not receive actions, rewards, body state, world
    state, wall-clock timestamps, or systematic neuron identities.
    """

    samples = _validated_samples(copy.deepcopy(history))
    first_sequence = samples[0]["sequence"] if samples else None
    last_sequence = samples[-1]["sequence"] if samples else None

    return {
        "schema": PROPRIOCEPTION_TEMPORAL_ANALYSIS_SCHEMA,
        "source": PROPRIOCEPTION_TEMPORAL_SOURCE,
        "human_only": True,
        "timebase": PROPRIOCEPTION_TEMPORAL_ANALYSIS_TIMEBASE,
        "sample_count": len(samples),
        "first_retained_sequence": first_sequence,
        "last_retained_sequence": last_sequence,
        "window_left_censoring_possible": bool(samples and first_sequence != 1),
        "channels": {
            channel: _channel_analysis(samples, channel) for channel in _CHANNEL_NAMES
        },
        "milliseconds_inferred": False,
        "step_cycle_phase_resolved": False,
        "inhibitory_lead_time_resolved": False,
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
