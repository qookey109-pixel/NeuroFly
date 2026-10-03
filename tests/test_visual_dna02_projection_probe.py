from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "visual_dna02_projection_probe.py"


def _load_probe():
    pytest.importorskip("numpy")
    spec = importlib.util.spec_from_file_location("visual_dna02_projection_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


def test_probe_script_parses_without_optional_runtime_dependencies() -> None:
    ast.parse(SCRIPT.read_text())


def test_probe_contract_is_read_only_and_learning_disabled() -> None:
    text = SCRIPT.read_text()
    assert 'SCHEMA = "neurofly-visual-dna02-projection-probe-v1"' in text
    assert "learning=False" in text
    assert "source_checkpoint_unchanged" in text
    assert '"production_checkpoint_mutated": False' in text
    assert '"behavioral_promotion_authorized": False' in text


def test_probe_conditions_are_fixed_and_sensory_only() -> None:
    probe = _load_probe()
    assert probe.CONDITIONS == (
        "uniform_control",
        "static_full_grating",
        "motion_left_outer",
        "motion_right_outer",
        "motion_full",
    )


def test_motion_probe_changes_only_requested_outer_screen_region() -> None:
    np = pytest.importorskip("numpy")
    probe = _load_probe()
    uniform = probe.make_probe_frame("uniform_control", 0, width=100, height=20)
    left = probe.make_probe_frame("motion_left_outer", 1, width=100, height=20)
    right = probe.make_probe_frame("motion_right_outer", 1, width=100, height=20)

    assert uniform.shape == (20, 100, 3)
    assert uniform.dtype == np.uint8

    left_end = int(100 * probe.OUTER_LEFT_END)
    right_start = int(100 * probe.OUTER_RIGHT_START)
    assert np.any(left[:, :left_end, :] != uniform[:, :left_end, :])
    assert np.all(left[:, left_end:, :] == uniform[:, left_end:, :])
    assert np.all(right[:, :right_start, :] == uniform[:, :right_start, :])
    assert np.any(right[:, right_start:, :] != uniform[:, right_start:, :])


def test_motion_probe_has_temporal_change_but_static_control_does_not() -> None:
    np = pytest.importorskip("numpy")
    probe = _load_probe()
    moving_a = probe.make_probe_frame("motion_full", 0)
    moving_b = probe.make_probe_frame("motion_full", 1)
    static_a = probe.make_probe_frame("static_full_grating", 0)
    static_b = probe.make_probe_frame("static_full_grating", 1)

    assert np.any(moving_a != moving_b)
    assert np.array_equal(static_a, static_b)
