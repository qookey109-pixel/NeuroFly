from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .olfaction import DANGER_ORN_TYPE, FOOD_ORN_TYPE, OLFACTION_MODEL
from .vision import VISION_MODEL
from .vision_adapter import retinalize_topdown_rgb


@dataclass(slots=True)
class BrainDecision:
    action: str
    backend: str
    telemetry: dict[str, Any]


class BrainBackend(Protocol):
    name: str

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision: ...

    def save(self, path: str | Path) -> None: ...


def _bilateral_type_indices(np: Any, annotations: Any, neuron_type: str) -> tuple[Any, Any, dict[str, Any]]:
    """Resolve bilateral MaleCNS neurons without assuming somaSide is populated.

    Sensory neurons can have no in-volume soma annotation even when their curated
    instance is explicitly lateralized (for example ORN_DM1_L / ORN_DM1_R).
    Use curated somaSide first and the instance suffix only as a documented
    fallback. Never infer side from body id or geometry.
    """

    types = annotations.type.fillna("").astype(str)
    type_mask = types.eq(neuron_type)
    sides = annotations.somaSide.fillna("").astype(str).str.upper()

    if "instance" in annotations.columns:
        instances = annotations["instance"].fillna("").astype(str)
    else:
        instances = types.map(lambda _: "")

    left_by_soma = type_mask & sides.eq("L")
    right_by_soma = type_mask & sides.eq("R")
    left_by_instance = type_mask & instances.str.endswith("_L")
    right_by_instance = type_mask & instances.str.endswith("_R")

    left_mask = left_by_soma | left_by_instance
    right_mask = right_by_soma | right_by_instance
    left = np.flatnonzero(left_mask.to_numpy())
    right = np.flatnonzero(right_mask.to_numpy())

    matched = type_mask & (left_mask | right_mask)
    unresolved = type_mask & ~matched
    report = {
        "type_neurons": int(type_mask.sum()),
        "left_neurons": int(len(left)),
        "right_neurons": int(len(right)),
        "left_from_soma_side": int(left_by_soma.sum()),
        "right_from_soma_side": int(right_by_soma.sum()),
        "left_from_instance_suffix": int((left_by_instance & ~left_by_soma).sum()),
        "right_from_instance_suffix": int((right_by_instance & ~right_by_soma).sum()),
        "unresolved_side": int(unresolved.sum()),
        "side_policy": "somaSide_then_curated_instance_suffix",
    }
    return left, right, report


STALL_HIGH_FREQUENCY_PATTERN = "neurofly-hf-stall-pulse-train-v1"
FOOD_TEMPORAL_GAIN = 1.5
FOOD_TEMPORAL_MAX_OFFSET = 0.20
DANGER_TEMPORAL_GAIN = 2.0
DANGER_TEMPORAL_MAX_OFFSET = 0.30
FOOD_ODOR_CURRENT_GAIN = 1.0
DANGER_ODOR_CURRENT_GAIN = 1.6
FOOD_FRONT_GAIN = 0.30
FOOD_BACK_ATTENUATION = 0.20
DANGER_FRONT_GAIN = 0.45
DANGER_BACK_ATTENUATION = 0.05
WALKING_DECODER = "neurofly-walking-decoder-v3"
WALKING_STEERING_TYPE = "DNa02"
WALKING_DRIVE_TYPE = "DNb05"
# Compatibility alias for downstream telemetry consumers. V3 treats this as
# a locomotor-drive population proxy, not as a claim that DNb05 is a sole
# forward command neuron.
WALKING_FORWARD_TYPE = WALKING_DRIVE_TYPE
WALKING_STEERING_THRESHOLD_HZ = 30.0


def _distributed_pulse_windows(
    total_steps: int,
    pulse_budget_steps: int,
    pulse_count: int,
) -> list[tuple[int, int]]:
    """Spread a fixed stimulation budget across evenly spaced short pulses."""
    total_steps = max(0, int(total_steps))
    pulse_budget_steps = max(0, min(total_steps, int(pulse_budget_steps)))
    pulse_count = max(0, min(int(pulse_count), total_steps))
    if total_steps == 0 or pulse_budget_steps == 0 or pulse_count == 0:
        return []

    starts = [(index * total_steps) // pulse_count for index in range(pulse_count)]
    base, extra = divmod(pulse_budget_steps, pulse_count)
    windows: list[tuple[int, int]] = []
    for index, start in enumerate(starts):
        width = base + (1 if index < extra else 0)
        if width <= 0:
            continue
        next_start = starts[index + 1] if index + 1 < len(starts) else total_steps
        end = min(total_steps, start + width, next_start)
        if end > start:
            windows.append((start, end))
    return windows


def _temporal_food_levels(
    left: float,
    right: float,
    previous_intensity: float | None,
) -> tuple[float, float, float, float]:
    """Encode whether appetitive odor is getting stronger or weaker over time."""
    raw_left = max(0.0, min(1.0, float(left)))
    raw_right = max(0.0, min(1.0, float(right)))
    intensity = (raw_left + raw_right) / 2.0
    delta = 0.0 if previous_intensity is None else intensity - float(previous_intensity)
    offset = max(
        -FOOD_TEMPORAL_MAX_OFFSET,
        min(FOOD_TEMPORAL_MAX_OFFSET, delta * FOOD_TEMPORAL_GAIN),
    )
    return (
        max(0.0, min(1.0, raw_left + offset)),
        max(0.0, min(1.0, raw_right + offset)),
        delta,
        intensity,
    )


def _temporal_danger_levels(
    left: float,
    right: float,
    previous_intensity: float | None,
) -> tuple[float, float, float, float]:
    """Encode whether aversive odor is getting stronger or weaker over time."""
    raw_left = max(0.0, min(1.0, float(left)))
    raw_right = max(0.0, min(1.0, float(right)))
    intensity = (raw_left + raw_right) / 2.0
    delta = 0.0 if previous_intensity is None else intensity - float(previous_intensity)
    offset = max(
        -DANGER_TEMPORAL_MAX_OFFSET,
        min(DANGER_TEMPORAL_MAX_OFFSET, delta * DANGER_TEMPORAL_GAIN),
    )
    return (
        max(0.0, min(1.0, raw_left + offset)),
        max(0.0, min(1.0, raw_right + offset)),
        delta,
        intensity,
    )


def _scaled_odor_current(base_current: float, level: float, gain: float) -> float:
    """Scale sensory current while keeping channel priority explicit and testable."""
    base = float(base_current)
    normalized = max(0.0, min(1.0, float(level)))
    multiplier = max(0.0, float(gain))
    return base * normalized * multiplier


def _longitudinal_odor_level(
    lateral_level: float,
    front: float,
    back: float,
    *,
    front_gain: float,
    back_attenuation: float,
) -> float:
    """Modulate bilateral ORN strength with egocentric front/back concentration."""
    base = max(0.0, min(1.0, float(lateral_level)))
    front_level = max(0.0, min(1.0, float(front)))
    back_level = max(0.0, min(1.0, float(back)))
    factor = 1.0 + float(front_gain) * front_level - float(back_attenuation) * back_level
    return max(0.0, min(1.0, base * factor))


def _walking_action(
    *,
    steering_left_hz: float,
    steering_right_hz: float,
    steering_spikes: int,
    drive_spikes: int,
    steering_threshold_hz: float,
) -> str:
    """Decode walking from neural activity only, without direct action forcing."""
    if int(drive_spikes) <= 0 and int(steering_spikes) <= 0:
        return "HOLD"

    difference = float(steering_right_hz) - float(steering_left_hz)
    if int(steering_spikes) > 0 and difference >= float(steering_threshold_hz):
        return "TURN_RIGHT"
    if int(steering_spikes) > 0 and difference <= -float(steering_threshold_hz):
        return "TURN_LEFT"

    # V3 requires a locomotor-drive population spike before emitting FORWARD.
    # DNa02-only activity can steer, but it cannot manufacture forward motion.
    if int(drive_spikes) > 0:
        return "FORWARD"
    return "HOLD"


class DemoBrain:
    """Small deterministic baseline used by CI and UI smoke tests."""

    name = "demo"

    def __init__(self) -> None:
        self.steps = 0

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.steps += 1
        preferred = None if context is None else context.get("demo_action")
        action = preferred if preferred in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"} else "FORWARD"
        return BrainDecision(
            action=action,
            backend=self.name,
            telemetry={
                "steps": self.steps,
                "reinforcement": reinforcement,
                "mode": "lightweight-baseline",
            },
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".demo.txt").write_text(f"steps={self.steps}\n")


class MaleCNSBrain:
    """Maze decoder on top of Stonkfly's pinned MaleCNS VisualMemoryBrain.

    The retained anatomy and visual dynamics come from the pinned Stonkfly
    implementation. NeuroFly now converts the omniscient maze renderer into an
    egocentric wide-field visual proxy before it reaches the retained visual
    system, and separately transduces bilateral virtual odors. These adapters are
    engineered interfaces inspired by fly sensory biology, not claims of exact
    retinal/olfactory physiology or a conscious animal reconstruction.
    """

    name = "malecns"

    def __init__(
        self,
        *,
        neural_ms: float = 50.0,
        neural_bin_ms: float = 10.0,
        pulse_ms: float = 20.0,
        pulse_current: float = 20.0,
        odor_current: float = 12.0,
        decoder_threshold_hz: float = WALKING_STEERING_THRESHOLD_HZ,
        learning: bool = True,
        checkpoint: str | Path | None = None,
    ) -> None:
        try:
            import numpy as np
            from stonkfly.neural.common import annotations
            from stonkfly.neural.visual import VisualMemoryBrain
        except Exception as exc:  # pragma: no cover - requires optional runtime
            raise RuntimeError(
                "MaleCNS runtime unavailable. Install `.[stonkfly]` and run "
                "`python -m stonkfly prepare` first."
            ) from exc

        if not math.isfinite(float(odor_current)) or float(odor_current) < 0:
            raise ValueError("odor_current must be finite and nonnegative")

        self.np = np
        self.neural_ms = float(neural_ms)
        self.neural_bin_ms = float(neural_bin_ms)
        self.pulse_ms = float(pulse_ms)
        self.pulse_current = float(pulse_current)
        self.odor_current = float(odor_current)
        self.decoder_threshold_hz = float(decoder_threshold_hz)
        self.learning = bool(learning)
        self.brain = VisualMemoryBrain()
        self.brain.weights_frozen = not self.learning
        self._last_visual_rgb: Any | None = None
        self._last_food_intensity: float | None = None
        self._last_danger_intensity: float | None = None

        a = annotations(self.brain.ids)
        types = a.type.fillna("").astype(str)
        (
            self.steering_left,
            self.steering_right,
            steering_side_report,
        ) = _bilateral_type_indices(np, a, WALKING_STEERING_TYPE)
        (
            self.walking_drive_left,
            self.walking_drive_right,
            walking_drive_side_report,
        ) = _bilateral_type_indices(np, a, WALKING_DRIVE_TYPE)
        self.walking_drive = np.unique(
            np.concatenate((self.walking_drive_left, self.walking_drive_right))
        )
        if (
            not len(self.steering_left)
            or not len(self.steering_right)
            or not len(self.walking_drive)
        ):
            raise RuntimeError(
                "Required walking decoder annotations are missing: "
                f"{WALKING_STEERING_TYPE}={steering_side_report}; "
                f"{WALKING_DRIVE_TYPE}={walking_drive_side_report}"
            )

        self.food_orn_left, self.food_orn_right, food_side_report = _bilateral_type_indices(
            np, a, FOOD_ORN_TYPE
        )
        (
            self.danger_orn_left,
            self.danger_orn_right,
            danger_side_report,
        ) = _bilateral_type_indices(np, a, DANGER_ORN_TYPE)
        if any(
            len(group) == 0
            for group in (
                self.food_orn_left,
                self.food_orn_right,
                self.danger_orn_left,
                self.danger_orn_right,
            )
        ):
            raise RuntimeError(
                "Required MaleCNS olfactory annotations are not resolvable bilaterally: "
                f"{FOOD_ORN_TYPE}={food_side_report}; {DANGER_ORN_TYPE}={danger_side_report}"
            )

        walking_drive_ids = [str(self.brain.ids[i]) for i in self.walking_drive]
        self.identities = {
            "steering_left": [str(self.brain.ids[i]) for i in self.steering_left],
            "steering_right": [str(self.brain.ids[i]) for i in self.steering_right],
            "walking_drive": walking_drive_ids,
            # Backward-compatible telemetry alias.
            "forward": walking_drive_ids,
        }
        self.motor_report = {
            "decoder": WALKING_DECODER,
            "steering_type": WALKING_STEERING_TYPE,
            "walking_drive_type": WALKING_DRIVE_TYPE,
            "forward_type": WALKING_FORWARD_TYPE,
            "steering": steering_side_report,
            "walking_drive": walking_drive_side_report,
            "forward": walking_drive_side_report,
            "steering_threshold_hz": self.decoder_threshold_hz,
            "dnpe017_gate_used": False,
            "direct_action_command": False,
        }
        self.olfaction_report = {
            "model": OLFACTION_MODEL,
            "engineered_proxy": True,
            "food": {
                "orn_type": FOOD_ORN_TYPE,
                "receptor_proxy": "Or42b",
                **food_side_report,
            },
            "danger": {
                "orn_type": DANGER_ORN_TYPE,
                "receptor_proxy": "Or56a/geosmin-like",
                **danger_side_report,
            },
            "max_external_current": self.odor_current,
            "food_current_gain": FOOD_ODOR_CURRENT_GAIN,
            "danger_current_gain": DANGER_ODOR_CURRENT_GAIN,
            "food_max_external_current": self.odor_current * FOOD_ODOR_CURRENT_GAIN,
            "danger_max_external_current": self.odor_current * DANGER_ODOR_CURRENT_GAIN,
            "directional_encoding": {
                "coordinate_frame": "egocentric-four-axis",
                "left_right": "bilateral ORN concentration contrast",
                "front_back": "longitudinal concentration modulation on bilateral ORNs",
                "food_front_gain": FOOD_FRONT_GAIN,
                "food_back_attenuation": FOOD_BACK_ATTENUATION,
                "danger_front_gain": DANGER_FRONT_GAIN,
                "danger_back_attenuation": DANGER_BACK_ATTENUATION,
                "direction_command": False,
            },
            "food_temporal_encoding": {
                "gain": FOOD_TEMPORAL_GAIN,
                "max_offset": FOOD_TEMPORAL_MAX_OFFSET,
                "direction_command": False,
            },
            "danger_temporal_encoding": {
                "gain": DANGER_TEMPORAL_GAIN,
                "max_offset": DANGER_TEMPORAL_MAX_OFFSET,
                "direction_command": False,
            },
            "validated": False,
        }
        self.vision_report = {
            "model": VISION_MODEL,
            "engineered_proxy": True,
            "input_policy": "egocentric-wide-panorama-not-topdown-map",
            "retained_visual_backend": "stonkfly.VisualMemoryBrain",
            "luminance_path": "mapped R1-R6 brightness inputs",
            "color_path": "mapped R8 blue-green proxy inputs",
            "motion_policy": "successive retinal frames drive retained temporal visual dynamics",
            "looming_policy": "near objects occupy increasing retinal area",
            "validated": False,
        }
        self.checkpoint_path = Path(checkpoint) if checkpoint else None
        if self.checkpoint_path and self.checkpoint_path.exists():
            self.brain.restore(self.checkpoint_path)

    def _decode(self, counts: Any) -> tuple[str, dict[str, Any]]:
        np = self.np
        seconds = self.neural_ms / 1000.0

        steering_left_hz = float(np.mean(counts[self.steering_left]) / seconds)
        steering_right_hz = float(np.mean(counts[self.steering_right]) / seconds)
        steering_difference_hz = steering_right_hz - steering_left_hz

        walking_drive_left_hz = (
            float(np.mean(counts[self.walking_drive_left]) / seconds)
            if len(self.walking_drive_left)
            else 0.0
        )
        walking_drive_right_hz = (
            float(np.mean(counts[self.walking_drive_right]) / seconds)
            if len(self.walking_drive_right)
            else 0.0
        )
        walking_drive_hz = float(np.mean(counts[self.walking_drive]) / seconds)

        steering_spikes = int(
            counts[self.steering_left].sum() + counts[self.steering_right].sum()
        )
        walking_drive_spikes = int(counts[self.walking_drive].sum())
        walking_spikes = steering_spikes + walking_drive_spikes

        action = _walking_action(
            steering_left_hz=steering_left_hz,
            steering_right_hz=steering_right_hz,
            steering_spikes=steering_spikes,
            drive_spikes=walking_drive_spikes,
            steering_threshold_hz=self.decoder_threshold_hz,
        )
        return action, {
            "motor_decoder": WALKING_DECODER,
            "steering_type": WALKING_STEERING_TYPE,
            "walking_drive_type": WALKING_DRIVE_TYPE,
            "forward_type": WALKING_FORWARD_TYPE,
            "left_hz": steering_left_hz,
            "right_hz": steering_right_hz,
            "difference_hz": steering_difference_hz,
            "walking_drive_hz": walking_drive_hz,
            "walking_drive_left_hz": walking_drive_left_hz,
            "walking_drive_right_hz": walking_drive_right_hz,
            "walking_drive_spikes": walking_drive_spikes,
            "steering_threshold_hz": self.decoder_threshold_hz,
            # Backward-compatible aliases retained for site-state consumers.
            "forward_hz": walking_drive_hz,
            "forward_left_hz": walking_drive_left_hz,
            "forward_right_hz": walking_drive_right_hz,
            "steering_spikes": steering_spikes,
            "forward_spikes": walking_drive_spikes,
            "walking_spikes": walking_spikes,
            "dnpe017_gate_used": False,
            "cell_ids": self.identities,
        }

    @staticmethod
    def _odor_level(channel: dict[str, Any], side: str) -> float:
        try:
            value = float(channel.get(side, 0.0))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid olfactory {side} intensity") from exc
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"Olfactory {side} intensity must be within [0, 1]")
        return value

    def _olfactory_stimulation(
        self,
        context: dict[str, Any] | None,
    ) -> tuple[list[tuple[Any, float]], dict[str, Any]]:
        olfaction = {} if context is None else (context.get("olfaction") or {})
        if not olfaction:
            self._last_food_intensity = None
            self._last_danger_intensity = None
            levels = {
                "food_left": 0.0,
                "food_right": 0.0,
                "food_raw_left": 0.0,
                "food_raw_right": 0.0,
                "food_front": 0.0,
                "food_back": 0.0,
                "food_longitudinal_bias": 0.0,
                "food_temporal_delta": 0.0,
                "food_temporal_trend": "steady",
                "danger_left": 0.0,
                "danger_right": 0.0,
                "danger_raw_left": 0.0,
                "danger_raw_right": 0.0,
                "danger_front": 0.0,
                "danger_back": 0.0,
                "danger_longitudinal_bias": 0.0,
                "danger_temporal_delta": 0.0,
                "danger_temporal_trend": "steady",
            }
            return [], levels
        if olfaction.get("model") != OLFACTION_MODEL:
            raise ValueError("Unsupported NeuroFly olfaction model")

        food = olfaction.get("food") or {}
        danger = olfaction.get("danger") or {}
        raw_food_left = self._odor_level(food, "left")
        raw_food_right = self._odor_level(food, "right")
        raw_food_front = self._odor_level(food, "front")
        raw_food_back = self._odor_level(food, "back")
        food_left, food_right, food_delta, food_intensity = _temporal_food_levels(
            raw_food_left,
            raw_food_right,
            self._last_food_intensity,
        )
        food_left = _longitudinal_odor_level(
            food_left,
            raw_food_front,
            raw_food_back,
            front_gain=FOOD_FRONT_GAIN,
            back_attenuation=FOOD_BACK_ATTENUATION,
        )
        food_right = _longitudinal_odor_level(
            food_right,
            raw_food_front,
            raw_food_back,
            front_gain=FOOD_FRONT_GAIN,
            back_attenuation=FOOD_BACK_ATTENUATION,
        )
        self._last_food_intensity = food_intensity
        if food_delta > 0.005:
            food_trend = "rising"
        elif food_delta < -0.005:
            food_trend = "falling"
        else:
            food_trend = "steady"

        raw_danger_left = self._odor_level(danger, "left")
        raw_danger_right = self._odor_level(danger, "right")
        raw_danger_front = self._odor_level(danger, "front")
        raw_danger_back = self._odor_level(danger, "back")
        danger_left, danger_right, danger_delta, danger_intensity = _temporal_danger_levels(
            raw_danger_left,
            raw_danger_right,
            self._last_danger_intensity,
        )
        danger_left = _longitudinal_odor_level(
            danger_left,
            raw_danger_front,
            raw_danger_back,
            front_gain=DANGER_FRONT_GAIN,
            back_attenuation=DANGER_BACK_ATTENUATION,
        )
        danger_right = _longitudinal_odor_level(
            danger_right,
            raw_danger_front,
            raw_danger_back,
            front_gain=DANGER_FRONT_GAIN,
            back_attenuation=DANGER_BACK_ATTENUATION,
        )
        self._last_danger_intensity = danger_intensity
        if danger_delta > 0.005:
            danger_trend = "rising"
        elif danger_delta < -0.005:
            danger_trend = "falling"
        else:
            danger_trend = "steady"

        levels = {
            "food_left": food_left,
            "food_right": food_right,
            "food_raw_left": raw_food_left,
            "food_raw_right": raw_food_right,
            "food_front": raw_food_front,
            "food_back": raw_food_back,
            "food_longitudinal_bias": raw_food_front - raw_food_back,
            "food_temporal_delta": food_delta,
            "food_temporal_trend": food_trend,
            "food_intensity": food_intensity,
            "danger_left": danger_left,
            "danger_right": danger_right,
            "danger_raw_left": raw_danger_left,
            "danger_raw_right": raw_danger_right,
            "danger_front": raw_danger_front,
            "danger_back": raw_danger_back,
            "danger_longitudinal_bias": raw_danger_front - raw_danger_back,
            "danger_temporal_delta": danger_delta,
            "danger_temporal_trend": danger_trend,
            "danger_intensity": danger_intensity,
        }
        pulses: list[tuple[Any, float]] = []
        for indices, level in (
            (self.food_orn_left, levels["food_left"]),
            (self.food_orn_right, levels["food_right"]),
        ):
            current = _scaled_odor_current(
                self.odor_current,
                level,
                FOOD_ODOR_CURRENT_GAIN,
            )
            if current > 0.0:
                pulses.append((indices, current))
        for indices, level in (
            (self.danger_orn_left, levels["danger_left"]),
            (self.danger_orn_right, levels["danger_right"]),
        ):
            current = _scaled_odor_current(
                self.odor_current,
                level,
                DANGER_ODOR_CURRENT_GAIN,
            )
            if current > 0.0:
                pulses.append((indices, current))
        levels["food_current_gain"] = FOOD_ODOR_CURRENT_GAIN
        levels["danger_current_gain"] = DANGER_ODOR_CURRENT_GAIN
        return pulses, levels

    def _visual_input(
        self,
        frame: Any,
        context: dict[str, Any] | None,
    ) -> tuple[Any, dict[str, Any]]:
        np = self.np
        raw_rgb = np.asarray(frame, dtype=np.uint8)
        if raw_rgb.ndim != 3 or raw_rgb.shape[2] != 3:
            raise ValueError("MaleCNSBrain requires an HxWx3 RGB frame")

        fly = None if context is None else context.get("fly")
        enemies = [] if context is None else (context.get("enemies") or [])
        rgb, vision = retinalize_topdown_rgb(
            raw_rgb,
            fly=fly if isinstance(fly, dict) else None,
            enemies=[dict(item) for item in enemies if isinstance(item, dict)],
        )

        visual_change = 0.0
        visual_left_change = 0.0
        visual_right_change = 0.0
        if self._last_visual_rgb is not None and self._last_visual_rgb.shape == rgb.shape:
            delta = np.abs(rgb.astype(np.int16) - self._last_visual_rgb.astype(np.int16))
            delta = delta.mean(axis=2) / 255.0
            visual_change = float(delta.mean())
            half = max(1, delta.shape[1] // 2)
            visual_left_change = float(delta[:, :half].mean())
            visual_right_change = float(delta[:, half:].mean())
        self._last_visual_rgb = rgb.copy()

        vision = dict(vision)
        vision.update(
            {
                "change": round(visual_change, 8),
                "left_change": round(visual_left_change, 8),
                "right_change": round(visual_right_change, 8),
            }
        )
        return rgb, vision

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        if reinforcement not in {"none", "reward", "aversive"}:
            raise ValueError(f"Unknown reinforcement: {reinforcement}")

        np = self.np
        rgb, vision = self._visual_input(frame, context)

        b = self.brain
        odor_pulses, odor_levels = self._olfactory_stimulation(context)
        counts = np.zeros(b.n, dtype=np.int32)
        compute_seconds = 0.0
        total_steps = round(self.neural_ms / b.dt)
        remaining = total_steps
        pulse_budget_steps = round(self.pulse_ms / b.dt) if reinforcement != "none" else 0
        context_data = context or {}
        high_frequency_stall = (
            reinforcement == "aversive"
            and context_data.get("_reinforcement_source") == "environment"
            and context_data.get("stall_stimulus_policy")
            == "neurofly-nondirectional-stall-aversive-hf-v3"
        )
        requested_pulses = (
            max(1, int(context_data.get("stall_stimulus_pulses_per_decision", 1)))
            if high_frequency_stall
            else (1 if reinforcement != "none" else 0)
        )
        pulse_windows = _distributed_pulse_windows(
            total_steps,
            pulse_budget_steps,
            requested_pulses,
        )
        delivered = 0
        cursor = 0
        pulse_index = 0

        while remaining:
            while pulse_index < len(pulse_windows) and cursor >= pulse_windows[pulse_index][1]:
                pulse_index += 1
            active = (
                pulse_index < len(pulse_windows)
                and pulse_windows[pulse_index][0] <= cursor < pulse_windows[pulse_index][1]
            )
            boundaries = [remaining, round(self.neural_bin_ms / b.dt)]
            if pulse_index < len(pulse_windows):
                start, end = pulse_windows[pulse_index]
                boundary = end if active else start
                if boundary > cursor:
                    boundaries.append(boundary - cursor)
            n = max(1, min(boundaries))

            stimulation = list(odor_pulses)
            if active:
                stimulation.append((b.circuit[reinforcement], self.pulse_current))
            current, elapsed = b.rgb_step(
                rgb,
                n * b.dt,
                learning=self.learning,
                stimulation=stimulation or None,
            )
            counts += current
            compute_seconds += elapsed
            remaining -= n
            cursor += n
            if active:
                delivered += n

        b.counts[:] = counts
        action, decoder = self._decode(counts)
        telemetry = {
            **decoder,
            "backend": self.name,
            "brain_ms": float(b.sim_ms),
            "compute_seconds": compute_seconds,
            "reinforcement": reinforcement,
            "reinforcement_source": context_data.get("_reinforcement_source", "none"),
            "reinforcement_pattern": (
                STALL_HIGH_FREQUENCY_PATTERN if high_frequency_stall else "single-pulse"
            ),
            "stimulus_ms": delivered * b.dt,
            "stimulus_pulse_count": len(pulse_windows),
            "stimulus_frequency_hz": (
                float(context_data.get("stall_stimulus_frequency_hz", 0.0))
                if high_frequency_stall
                else 0.0
            ),
            "reward_spikes": int(counts[b.circuit["reward"]].sum()),
            "aversive_spikes": int(counts[b.circuit["aversive"]].sum()),
            "kc_spikes": int(counts[b.circuit["kc"]].sum()),
            "total_spikes": int(counts.sum()),
            "vision_model": VISION_MODEL,
            "vision": vision,
            "visual_change": vision.get("change", 0.0),
            "visual_left_change": vision.get("left_change", 0.0),
            "visual_right_change": vision.get("right_change", 0.0),
            "vision_report": self.vision_report,
            "olfaction_model": OLFACTION_MODEL,
            "olfaction": odor_levels,
            "food_odor_spikes": int(
                counts[self.food_orn_left].sum() + counts[self.food_orn_right].sum()
            ),
            "danger_odor_spikes": int(
                counts[self.danger_orn_left].sum() + counts[self.danger_orn_right].sum()
            ),
            "olfaction_report": self.olfaction_report,
            "memory": b.memory(),
        }
        return BrainDecision(action=action, backend=self.name, telemetry=telemetry)

    def save(self, path: str | Path) -> None:
        self.brain.checkpoint(Path(path))


def brain_status() -> dict[str, Any]:
    """Report whether the pinned Stonkfly package and prepared graph are usable."""

    status: dict[str, Any] = {
        "backend": "malecns",
        "installed": False,
        "prepared": False,
        "release": None,
        "neurons": None,
        "directed_edges": None,
        "error": None,
    }
    try:
        import stonkfly  # noqa: F401

        status["installed"] = True
        from stonkfly.data import verify

        verified = verify()
        status.update(
            prepared=True,
            release=verified.get("release"),
            neurons=verified.get("neurons"),
            directed_edges=verified.get("directed_edges"),
        )
    except Exception as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
    return status
