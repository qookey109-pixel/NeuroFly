from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tactile_subtype_latency_screen.py"


def test_tactile_latency_screen_parses() -> None:
    ast.parse(SCRIPT.read_text())


def test_tactile_latency_screen_is_diagnostic_only() -> None:
    text = SCRIPT.read_text()
    assert 'SCHEMA = "neurofly-tactile-subtype-latency-screen-v1"' in text
    assert "TACTILE_CURRENT = 8.0" in text
    assert "WINDOW_MS = 50.0" in text
    assert "WINDOWS = 5" in text
    assert '"production_runtime_authorized": False' in text
    assert '"tactile_subtype_selected": False' in text
    assert '"temporal_kernel_selected": False' in text
    assert '"decoder_change_authorized": False' in text
    assert "source_before != source_after" in text


def test_latency_screen_stimulates_only_first_window() -> None:
    text = SCRIPT.read_text()
    assert "if window_index == 0 and len(target)" in text
    assert "Windows 1..4 test propagation" in text
