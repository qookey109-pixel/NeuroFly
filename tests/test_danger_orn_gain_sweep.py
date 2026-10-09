from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/danger_orn_gain_sweep.py"


def _load():
    pytest.importorskip("numpy")
    spec = importlib.util.spec_from_file_location("danger_orn_gain_sweep", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gain_sweep_parses_without_optional_dependencies() -> None:
    ast.parse(SCRIPT.read_text())


def test_gain_sweep_cannot_change_production_checkpoint_or_action() -> None:
    source = SCRIPT.read_text()
    assert "learning=False" in source
    assert "weights_frozen = True" in source
    assert "finally:" in source
    assert "runtime.DANGER_ODOR_CURRENT_GAIN = baseline_gain" in source
    assert '"maze_actions_executed": False' in source
    assert '"production_gain_change_authorized": False' in source


def test_gain_sweep_values_are_frozen() -> None:
    mod = _load()
    assert mod.DANGER_GAINS == (1.6, 2.4, 3.2)
    assert mod.FOOD_GAIN == 1.0
    assert mod.PROBE_FRAMES == 24
    assert mod.WARMUP_FRAMES == 4
