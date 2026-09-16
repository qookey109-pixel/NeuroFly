from __future__ import annotations

import copy
from collections import deque
from typing import Any

from .proprioception import (
    PROPRIOCEPTION_ENCODING,
    PROPRIOCEPTION_MODEL,
    proprioceptive_channel_levels,
)
from .sensory_contract import assert_unprivileged_agent_input


PROPRIOCEPTION_TEMPORAL_SCHEMA = "neurofly-proprioception-temporal-observability-v0.1"
PROPRIOCEPTION_TEMPORAL_SOURCE = "verified-neural-handoff-receptor-domain"
DEFAULT_PROPRIOCEPTION_HISTORY_CAPACITY = 36
MAX_PROPRIOCEPTION_HISTORY_CAPACITY = 36

_EXPECTED_RECEPTOR_KEYS = {
    "model",
    "available",
    "encoding",
    "channels",
    "claw_position_available",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "engineering_proxy",
}
_CHANNEL_NAMES = (
    "hook_extension",
    "hook_flexion",
    "club_motion",
    "club_vibration",
)


def freeze_proprioception_handoff_sample(
    payload: dict[str, Any],
    *,
    sequence: int,
) -> dict[str, Any]:
    """Freeze one exact receptor-domain payload after neural-handoff validation.

    This function is intentionally stricter than the generic channel parser. It
    accepts only the current engineering receptor contract and emits a human-only
    diagnostic record. It never assigns a MaleCNS systematic type and never
    creates a current/stimulation target.
    """

    if not isinstance(payload, dict):
        raise ValueError("Proprioception handoff sample must be an object")
    if set(payload) != _EXPECTED_RECEPTOR_KEYS:
        raise ValueError("Unexpected proprioception handoff payload fields")
    if payload.get("engineering_proxy") is not True:
        raise ValueError("Temporal observability requires the engineering receptor proxy")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ValueError("Temporal sample sequence must be a positive integer")

    levels = proprioceptive_channel_levels(payload)
    assert_unprivileged_agent_input({"proprioception": payload})

    return {
        "sequence": sequence,
        "source": PROPRIOCEPTION_TEMPORAL_SOURCE,
        "model": PROPRIOCEPTION_MODEL,
        "encoding": PROPRIOCEPTION_ENCODING,
        "channels": {name: float(levels[name]) for name in _CHANNEL_NAMES},
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "systematic_type_mapping_exposed": False,
        "current_calibration_authorized": False,
        "neural_payload_eligible": False,
    }


class ProprioceptionTemporalRecorder:
    """Bounded, human-only history of exact neural-handoff receptor samples."""

    def __init__(self, *, capacity: int = DEFAULT_PROPRIOCEPTION_HISTORY_CAPACITY) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise ValueError("Proprioception history capacity must be an integer")
        if not 1 <= capacity <= MAX_PROPRIOCEPTION_HISTORY_CAPACITY:
            raise ValueError(
                f"Proprioception history capacity must stay within 1..{MAX_PROPRIOCEPTION_HISTORY_CAPACITY}"
            )
        self.capacity = capacity
        self._samples: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._next_sequence = 1

    def observe_neural_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Record one receptor payload that was actually used for a neural handoff."""

        frozen = freeze_proprioception_handoff_sample(
            copy.deepcopy(payload),
            sequence=self._next_sequence,
        )
        self._samples.append(frozen)
        self._next_sequence += 1
        return copy.deepcopy(frozen)

    def reset(self) -> None:
        """Clear diagnostic history without changing any body or neural state."""

        self._samples.clear()
        self._next_sequence = 1

    def snapshot(self) -> dict[str, Any]:
        """Return a copy-safe human diagnostic history contract."""

        return {
            "schema": PROPRIOCEPTION_TEMPORAL_SCHEMA,
            "source": PROPRIOCEPTION_TEMPORAL_SOURCE,
            "human_only": True,
            "capacity": self.capacity,
            "sample_count": len(self._samples),
            "samples": copy.deepcopy(list(self._samples)),
            "history_persistence_enabled": False,
            "systematic_type_mapping_exposed": False,
            "current_calibration_authorized": False,
            "stimulation_enabled": False,
            "runtime_transduction_enabled": False,
            "neural_payload_eligible": False,
        }
