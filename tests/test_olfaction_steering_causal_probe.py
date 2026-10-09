from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "olfaction_steering_causal_probe.py"


def _load_probe():
    pytest.importorskip("numpy")
    spec = importlib.util.spec_from_file_location("olfaction_steering_causal_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_is_syntactically_valid_without_optional_dependencies() -> None:
    ast.parse(SCRIPT.read_text())


def test_probe_never_trains_or_mutates_production_state() -> None:
    source = SCRIPT.read_text()
    assert "learning=False" in source
    assert "weights_frozen = True" in source
    assert "sha_before != sha_after" in source
    assert '"maze_actions_executed": False' in source
    assert '"decoder_change_authorized": False' in source


def test_probe_conditions_are_symmetrical() -> None:
    probe = _load_probe()
    assert probe.CONDITIONS == (
        "neutral",
        "food_left",
        "food_right",
        "danger_left",
        "danger_right",
        "food_bilateral",
        "danger_bilateral",
    )
    assert probe.make_context("food_left")["olfaction"]["food"]["left"] == 0.8
    assert probe.make_context("food_left")["olfaction"]["food"]["right"] == 0.0
    assert probe.make_context("food_right")["olfaction"]["food"]["left"] == 0.0
    assert probe.make_context("food_right")["olfaction"]["food"]["right"] == 0.8
    assert probe.make_context("danger_left")["olfaction"]["danger"]["left"] == 0.8
    assert probe.make_context("danger_right")["olfaction"]["danger"]["right"] == 0.8
    assert probe.make_context("neutral")["curriculum_stage"] == 1


def test_probe_forbids_unknown_conditions() -> None:
    probe = _load_probe()
    with pytest.raises(ValueError):
        probe.make_context("target_direction_right")
