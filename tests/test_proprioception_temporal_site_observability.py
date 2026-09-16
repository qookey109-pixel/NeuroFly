from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "site" / "all-clear-history.js"
INDEX = ROOT / "site" / "index.html"


def test_temporal_hud_validates_bounded_human_only_contract() -> None:
    source = SCRIPT.read_text()

    for required in (
        "neurofly-proprioception-temporal-observability-v0.1",
        "verified-neural-handoff-receptor-domain",
        "TEMPORAL_MAX_CAPACITY = 36",
        "record.human_only === true",
        "record.history_persistence_enabled === false",
        "record.systematic_type_mapping_exposed === false",
        "record.current_calibration_authorized === false",
        "record.stimulation_enabled === false",
        "record.runtime_transduction_enabled === false",
        "record.neural_payload_eligible === false",
        "sequence === previousSequence + 1",
        "sampleCount <= capacity",
        "samples.slice(-8)",
        "Temporal receptor history 不可用 · FAIL CLOSED",
    ):
        assert required in source


def test_temporal_hud_consumes_both_fallback_and_live_relay_state() -> None:
    source = SCRIPT.read_text()

    assert source.count("renderTemporalProprioception(view);") == 2
    assert "./malecns-state.json" in source
    assert "new EventSource(LIVE_RELAY)" in source
    assert "proprioception_temporal" in source


def test_temporal_hud_preserves_systematic_type_and_current_locks() -> None:
    source = SCRIPT.read_text()

    assert "沒有 executable hook_extension/flexion → SNpp39/41 alias" in source
    assert "沒有 proprioceptive current" in source
    assert "human diagnostics 不回流成 neural input" in source
    assert "event analysis 也不會回流成 neural input" in source


def test_temporal_hud_cache_buster_moves_past_live_only_version() -> None:
    index = INDEX.read_text()

    assert "all-clear-history.js?v=proprio-temporal-runtime-1" in index
    assert "all-clear-history.js?v=proprio-live-1" not in index
