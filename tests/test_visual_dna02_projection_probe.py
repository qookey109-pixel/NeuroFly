from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "visual_dna02_projection_probe.py"
SPEC = importlib.util.spec_from_file_location("visual_dna02_projection_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_probe_conditions_are_fixed_and_sensory_only() -> None:
    assert probe.CONDITIONS == (
        "uniform_control",
        "static_full_grating",
        "motion_left_outer",
        "motion_right_outer",
        "motion_full",
    )


def test_motion_probe_changes_only_requested_outer_screen_region() -> None:
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
    moving_a = probe.make_probe_frame("motion_full", 0)
    moving_b = probe.make_probe_frame("motion_full", 1)
    static_a = probe.make_probe_frame("static_full_grating", 0)
    static_b = probe.make_probe_frame("static_full_grating", 1)

    assert np.any(moving_a != moving_b)
    assert np.array_equal(static_a, static_b)
