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
        odor_current: float = 8.0,
        decoder_threshold_hz: float = 2.0,
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

        a = annotations(self.brain.ids)
        types = a.type.fillna("")
        sides = a.somaSide.fillna("")
        self.left = np.flatnonzero(types.eq("DNp20") & sides.eq("L"))
        self.right = np.flatnonzero(types.eq("DNp20") & sides.eq("R"))
        self.gate = np.flatnonzero(types.eq("DNpe017"))
        if not len(self.left) or not len(self.right) or not len(self.gate):
            raise RuntimeError("Required DNp20/DNpe017 readout annotations are missing")

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

        self.identities = {
            "left": [str(self.brain.ids[i]) for i in self.left],
            "right": [str(self.brain.ids[i]) for i in self.right],
            "gate": [str(self.brain.ids[i]) for i in self.gate],
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
        left_hz = float(np.mean(counts[self.left]) / seconds)
        right_hz = float(np.mean(counts[self.right]) / seconds)
        difference = right_hz - left_hz
        gate_spikes = int(counts[self.gate].sum())
        if not gate_spikes:
            action = "HOLD"
        elif difference >= self.decoder_threshold_hz:
            action = "TURN_RIGHT"
        elif difference <= -self.decoder_threshold_hz:
            action = "TURN_LEFT"
        else:
            action = "FORWARD"
        return action, {
            "left_hz": left_hz,
            "right_hz": right_hz,
            "difference_hz": difference,
            "gate_spikes": gate_spikes,
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
            levels = {
                "food_left": 0.0,
                "food_right": 0.0,
                "danger_left": 0.0,
                "danger_right": 0.0,
            }
            return [], levels
        if olfaction.get("model") != OLFACTION_MODEL:
            raise ValueError("Unsupported NeuroFly olfaction model")

        food = olfaction.get("food") or {}
        danger = olfaction.get("danger") or {}
        levels = {
            "food_left": self._odor_level(food, "left"),
            "food_right": self._odor_level(food, "right"),
            "danger_left": self._odor_level(danger, "left"),
            "danger_right": self._odor_level(danger, "right"),
        }
        pulses: list[tuple[Any, float]] = []
        for indices, level in (
            (self.food_orn_left, levels["food_left"]),
            (self.food_orn_right, levels["food_right"]),
            (self.danger_orn_left, levels["danger_left"]),
            (self.danger_orn_right, levels["danger_right"]),
        ):
            if level > 0.0 and self.odor_current > 0.0:
                pulses.append((indices, self.odor_current * level))
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
        remaining = round(self.neural_ms / b.dt)
        pulse = round(self.pulse_ms / b.dt) if reinforcement != "none" else 0
        delivered = 0

        while remaining:
            n = min(remaining, round(self.neural_bin_ms / b.dt))
            if pulse:
                n = min(n, pulse)
            stimulation = list(odor_pulses)
            if pulse:
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
            if pulse:
                delivered += n
                pulse -= n

        b.counts[:] = counts
        action, decoder = self._decode(counts)
        telemetry = {
            **decoder,
            "backend": self.name,
            "brain_ms": float(b.sim_ms),
            "compute_seconds": compute_seconds,
            "reinforcement": reinforcement,
            "stimulus_ms": delivered * b.dt,
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
