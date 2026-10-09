from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tactile_subtype_downstream_screen.py"


def test_tactile_subtype_screen_parses() -> None:
    ast.parse(SCRIPT.read_text())


def test_tactile_subtype_screen_is_diagnostic_only() -> None:
    text = SCRIPT.read_text()
    assert 'SCHEMA = "neurofly-tactile-subtype-downstream-screen-v1"' in text
    assert "TACTILE_CURRENT = 8.0" in text
    assert "NEURAL_MS = 50.0" in text
    for neuron_type in ("SNta20", "SNta26", "SNta27", "SNta28", "SNta34", "SNta37"):
        assert neuron_type in text
    assert '"production_runtime_authorized": False' in text
    assert '"tactile_subtype_selected": False' in text
    assert '"decoder_change_authorized": False' in text
    assert "source_before != source_after" in text


def test_tactile_subtype_screen_reads_frozen_evidence() -> None:
    text = SCRIPT.read_text()
    assert "tactile_current_calibration_v1.json" in text
    assert "tactile_leg_functional_crosswalk_v02.json" in text
    assert "41592fd805bbfa19f73959af24479d12770e10866ed05e8fc85a86eac198f462" in text
