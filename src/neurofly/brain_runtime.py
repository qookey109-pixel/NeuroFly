from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


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
    implementation. The maze action mapping below is NeuroFly-specific and is
    deliberately treated as an engineered interface rather than biology.
    """

    name = "malecns"

    def __init__(
        self,
        *,
        neural_ms: float = 500.0,
        neural_bin_ms: float = 10.0,
        pulse_ms: float = 200.0,
        pulse_current: float = 20.0,
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

        self.np = np
        self.neural_ms = float(neural_ms)
        self.neural_bin_ms = float(neural_bin_ms)
        self.pulse_ms = float(pulse_ms)
        self.pulse_current = float(pulse_current)
        self.decoder_threshold_hz = float(decoder_threshold_hz)
        self.learning = bool(learning)
        self.brain = VisualMemoryBrain()
        self.brain.weights_frozen = not self.learning

        a = annotations(self.brain.ids)
        types = a.type.fillna("")
        sides = a.somaSide.fillna("")
        self.left = np.flatnonzero(types.eq("DNp20") & sides.eq("L"))
        self.right = np.flatnonzero(types.eq("DNp20") & sides.eq("R"))
        self.gate = np.flatnonzero(types.eq("DNpe017"))
        if not len(self.left) or not len(self.right) or not len(self.gate):
            raise RuntimeError("Required DNp20/DNpe017 readout annotations are missing")

        self.identities = {
            "left": [str(self.brain.ids[i]) for i in self.left],
            "right": [str(self.brain.ids[i]) for i in self.right],
            "gate": [str(self.brain.ids[i]) for i in self.gate],
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
        rgb = np.asarray(frame, dtype=np.uint8)
        if rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("MaleCNSBrain requires an HxWx3 RGB frame")

        b = self.brain
        counts = np.zeros(b.n, dtype=np.int32)
        compute_seconds = 0.0
        remaining = round(self.neural_ms / b.dt)
        pulse = round(self.pulse_ms / b.dt) if reinforcement != "none" else 0
        delivered = 0

        while remaining:
            n = min(remaining, round(self.neural_bin_ms / b.dt))
            if pulse:
                n = min(n, pulse)
            stimulation = (
                (b.circuit[reinforcement], self.pulse_current) if pulse else None
            )
            current, elapsed = b.rgb_step(
                rgb,
                n * b.dt,
                learning=self.learning,
                stimulation=stimulation,
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
