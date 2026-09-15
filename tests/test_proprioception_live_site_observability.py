from __future__ import annotations

from pathlib import Path


OBSERVER_PATH = Path("site/all-clear-history.js")


def test_site_reads_human_only_receptor_diagnostics() -> None:
    source = OBSERVER_PATH.read_text()

    required = (
        "human_diagnostics?.proprioception",
        "latest-neural-handoff-receptor-domain",
        "proprioceptionHookExtension",
        "proprioceptionHookFlexion",
        "proprioceptionClubMotion",
        "proprioceptionClubVibration",
        "systematic_type_mapping_exposed === false",
        "stimulation_enabled === false",
        "runtime_transduction_enabled === false",
    )
    for marker in required:
        assert marker in source


def test_site_has_distinct_receptor_and_control_plane_sections() -> None:
    source = OBSERVER_PATH.read_text()

    assert "LIVE RECEPTOR INPUT" in source
    assert "證據狀態 / CONTROL PLANE" in source
    assert "renderLiveProprioception" in source
    assert "renderProprioceptionSemantics" in source
