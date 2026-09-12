import json
from pathlib import Path

import pytest

import neurofly.preflight as preflight
import neurofly.smoke as smoke
from neurofly.brain_runtime import BrainDecision, DemoBrain
from neurofly.maze_runtime import MazeSession
from neurofly.server import MazeService
from neurofly.site_state import build_site_state, publish_site_state, verify_receipt


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


def test_real_smoke_writes_hashed_receipt_and_verified_trajectory(tmp_path, monkeypatch) -> None:
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
    assert saved["schema"] == "neurofly-real-smoke-v2"
    assert saved["backend"] == "malecns"
    assert saved["neural_activity_verified"] is True
    assert saved["steps"] == 1
    assert saved["observations"][0]["total_spikes"] == 42
    assert saved["observations"][0]["neural_activity_verified"] is True
    assert saved["trajectory"][0]["brain"]["backend"] == "malecns"
    assert saved["trajectory"][0]["brain"]["telemetry"]["total_spikes"] == 42
    assert len(saved["receipt_sha256"]) == 64
    verify_receipt(saved)


def test_site_state_publishes_only_verified_receipt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        smoke,
        "collect_preflight",
        lambda: {"ready": True, "low_memory_guard": False, "checks": []},
    )
    monkeypatch.setattr(smoke, "MaleCNSBrain", _FakeBrain)
    receipt_path = tmp_path / "receipt.json"
    smoke.run_real_smoke(
        steps=2,
        checkpoint=tmp_path / "brain.npz",
        receipt=receipt_path,
        seed=7,
    )
    output = tmp_path / "site-state.json"
    state = publish_site_state(receipt_path=receipt_path, output_path=output)
    saved = json.loads(output.read_text())
    assert state["verified"] is True
    assert saved["backend"] == "malecns"
    assert saved["mode"] == "recorded-malecns"
    assert len(saved["trajectory"]) == 2
    assert saved["source_receipt_sha256"] == json.loads(receipt_path.read_text())["receipt_sha256"]


def test_site_state_rejects_tampered_or_non_neural_receipt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        smoke,
        "collect_preflight",
        lambda: {"ready": True, "low_memory_guard": False, "checks": []},
    )
    monkeypatch.setattr(smoke, "MaleCNSBrain", _FakeBrain)
    receipt_path = tmp_path / "receipt.json"
    receipt = smoke.run_real_smoke(
        steps=1,
        checkpoint=tmp_path / "brain.npz",
        receipt=receipt_path,
        seed=7,
    )

    tampered = dict(receipt)
    tampered["trajectory"] = [dict(receipt["trajectory"][0])]
    tampered["trajectory"][0]["last_action"] = "NOT_A_REAL_ACTION"
    with pytest.raises(ValueError, match="SHA-256"):
        verify_receipt(tampered)

    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    unsigned["trajectory"][0]["brain"]["telemetry"]["total_spikes"] = 0
    unsigned["receipt_sha256"] = smoke._digest_json(unsigned)
    with pytest.raises(ValueError, match="neural activity"):
        build_site_state(unsigned)


def test_cloud_bootstrap_state_is_paused_and_explicit() -> None:
    session = MazeSession(DemoBrain(), checkpoint=None, seed=9)
    service = MazeService(
        session,
        running=False,
        phase="preparing-malecns",
        tick_seconds=0.6,
    )
    state = service.state()
    assert state["runtime"]["running"] is False
    assert state["runtime"]["phase"] == "preparing-malecns"
    assert state["brain"]["backend"] == "demo"

    replacement = MazeSession(_FakeBrain(), checkpoint=None, seed=9)
    service.replace_session(replacement, phase="malecns-ready")
    service.running = True
    promoted = service.state()
    assert promoted["runtime"]["phase"] == "malecns-ready"
    assert promoted["brain"]["backend"] == "malecns"
