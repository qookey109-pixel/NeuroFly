from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "site" / "all-clear-history.js"


def test_site_event_analysis_uses_only_reviewed_temporal_history_contract() -> None:
    source = SCRIPT.read_text()

    for required in (
        "TEMPORAL_EVENT_TIMEBASE = 'decision-index-only'",
        "exactKeys(record, TEMPORAL_HISTORY_KEYS)",
        "exactKeys(sample, TEMPORAL_SAMPLE_KEYS)",
        "const active = level > 0;",
        "left_censored: index === 0",
        "previousActive === false",
        "previousActive === true",
        "right_censored = true",
        "window_left_censoring_possible",
        "milliseconds_inferred: false",
        "step_cycle_phase_resolved: false",
        "inhibitory_lead_time_resolved: false",
        "browser-local human-only derived",
        "ms / biological phase / 9A lead time 未解析",
    ):
        assert required in source

    assert "view?.human_diagnostics?.proprioception_temporal;" in source
    assert "human_diagnostics?.proprioception_temporal_analysis" not in source


def test_site_event_derivation_does_not_use_privileged_or_identity_fields() -> None:
    source = SCRIPT.read_text()
    body = source.split("function deriveTemporalEventAnalysis(record) {", 1)[1].split(
        "function renderTemporalEventAnalysis(record) {", 1
    )[0]

    for forbidden in (
        "reward",
        "motor_command",
        "world_state",
        "private_body",
        "SNpp39",
        "SNpp41",
        "systematic_type",
    ):
        assert forbidden not in body


def test_site_event_visualization_exposes_only_descriptive_decision_index_metrics() -> None:
    source = SCRIPT.read_text()

    for required in (
        "observed_start_sequence",
        "observed_end_sequence",
        "observed_duration_decisions",
        "peak_level",
        "active_sample_count",
        "rising_transition_count_within_window",
        "falling_transition_count_within_window",
        "event_count_observed",
        "L-censored",
        "R-censored",
    ):
        assert required in source

    assert "TEMPORAL EVENT ANALYSIS" in source
    assert "event analysis 也不會回流成 neural input" in source
