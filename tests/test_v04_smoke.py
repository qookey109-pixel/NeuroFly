import json
from pathlib import Path

import neurofly.preflight as preflight
import neurofly.smoke as smoke
from neurofly.brain_runtime import BrainDecision


def test_preflight_report_has_stable_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_total_memory_bytes", lambda: 16 * preflight.GIB)
    monkeypatch.setattr(preflight.importlib.util, "find_spec", lambda name: None)
    report = preflight.collect_preflight(data_dir=tmp_path)
    assert report["ready"] is False
    assert report["memory_gib"] == 16.0
    assert report["recommended_ram_gib"] == 16.0
    assert {item["name"] for item in report["checks"]} >= {
        "python",
        "compiler",
        "stonkfly",
        "prepared_graph",
        "memory_recommended",
        "disk_recommended",
    }


class _FakeBrain:
    name = "malecns"

    def __init__(self, *, checkpoint=None):
        self.checkpoint = checkpoint

    def decide(self, frame, reinforcement="none", *, context=None):
        return BrainDecision(
            action="FORWARD",
            backend="malecns",
            telemetry={
                "brain_ms": 500.0,
                "compute_seconds": 0.01,
                "total_spikes": 42,
                "reward_spikes": 1,
                "aversive_spikes": 0,
                "kc_spikes": 7,
                "memory": {"sha256": "abc123"},
            },
        )

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"fake-brain")


def test_real_smoke_writes_hashed_receipt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        smoke,
        "collect_preflight",
        lambda: {"ready": True, "low_memory_guard": False, "checks": []},
    )
    monkeypatch.setattr(smoke, "MaleCNSBrain", _FakeBrain)
    checkpoint = tmp_path / "brain.npz"
    receipt = tmp_path / "receipt.json"
    result = smoke.run_real_smoke(
        steps=1,
        checkpoint=checkpoint,
        receipt=receipt,
        seed=7,
    )
    saved = json.loads(receipt.read_text())
    assert result["passed"] is True
    assert saved["backend"] == "malecns"
    assert saved["steps"] == 1
    assert saved["observations"][0]["total_spikes"] == 42
    assert len(saved["receipt_sha256"]) == 64
