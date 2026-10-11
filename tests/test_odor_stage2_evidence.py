from __future__ import annotations

import pytest

from neurofly.odor_stage2_evidence import compare_candidate


def _arm(**changes: float | int | str | None) -> dict:
    base = {
        "source_sha256": "same-source",
        "initial_stage": 2,
        "steps": 600,
        "blocked_forward_fraction": 0.55,
        "near_wall_forward_fraction": 0.70,
        "revisit_fraction_mean": 0.74,
        "deaths_per_1000_decisions": 6.0,
        "food_events": 100,
        "best_episode_food_progress": 45,
        "stage2_clear_delta": 0,
        "world_tick_delta": 12,
        "discarded_decision_count": 0,
    }
    return {**base, **changes}


def test_improving_exploratory_signal_never_authorizes_production() -> None:
    baseline = _arm()
    candidate = _arm(
        blocked_forward_fraction=0.50,
        near_wall_forward_fraction=0.69,
        revisit_fraction_mean=0.73,
        deaths_per_1000_decisions=6.5,
        food_events=110,
        best_episode_food_progress=50,
        stage2_clear_delta=1,
    )
    result = compare_candidate(baseline, candidate)
    assert result["candidate_minus_baseline"]["blocked_forward_fraction"] == pytest.approx(-0.05)
    assert result["candidate_minus_baseline"]["stage2_clear_delta"] == 1
    assert result["exposure_comparable"] is True
    assert result["exploratory_signal_only"] is True
    assert result["repeat_study_required"] is True
    assert result["production_promotion_authorized"] is False


def test_regression_rejects_candidate_even_with_more_food() -> None:
    candidate = _arm(blocked_forward_fraction=0.61, food_events=120)
    result = compare_candidate(_arm(), candidate)
    assert result["exploratory_signal_only"] is False


@pytest.mark.parametrize("changes", [
    {"world_tick_delta": 0},
    {"world_tick_delta": 20},
    {"discarded_decision_count": 15},
])
def test_unmatched_predator_exposure_must_reject_even_good_behavior(changes: dict) -> None:
    candidate = _arm(
        blocked_forward_fraction=0.50,
        near_wall_forward_fraction=0.69,
        revisit_fraction_mean=0.73,
        deaths_per_1000_decisions=6.5,
        food_events=110,
        stage2_clear_delta=1,
        **changes,
    )
    result = compare_candidate(_arm(), candidate)
    assert result["sufficient_data"] is True
    assert result["exposure_comparable"] is False
    assert result["exploratory_signal_only"] is False
    assert result["production_promotion_authorized"] is False


def test_missing_world_ticks_fails_closed() -> None:
    baseline = _arm()
    baseline.pop("world_tick_delta")
    result = compare_candidate(baseline, _arm())
    assert result["sufficient_data"] is True
    assert result["exposure_comparable"] is False
    assert result["exploratory_signal_only"] is False


def test_missing_behavior_metrics_cannot_pass() -> None:
    candidate = _arm(blocked_forward_fraction=None)
    result = compare_candidate(_arm(), candidate)
    assert result["sufficient_data"] is False
    assert result["exploratory_signal_only"] is False


@pytest.mark.parametrize("changes", [
    {"initial_stage": 1},
    {"source_sha256": "other-state"},
    {"steps": 601},
])
def test_mismatched_trials_fail_closed(changes: dict) -> None:
    with pytest.raises(ValueError):
        compare_candidate(_arm(), _arm(**changes))
