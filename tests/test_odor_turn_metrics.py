from __future__ import annotations

import pytest

from neurofly.odor_turn_metrics import summarize_decoded_turns


def test_danger_left_requires_observed_right_turn_to_count_away() -> None:
    result = summarize_decoded_turns(
        ["TURN_RIGHT", "TURN_RIGHT", "TURN_LEFT", "FORWARD", "HOLD"],
        condition="danger_left",
    )
    assert result["decision_count"] == 5
    assert result["expected_away_turn"] == "TURN_RIGHT"
    assert result["action_counts"] == {
        "TURN_LEFT": 1, "TURN_RIGHT": 2, "FORWARD": 1, "HOLD": 1,
    }
    assert result["turn_fraction"] == pytest.approx(3 / 5)
    assert result["away_turn_fraction"] == pytest.approx(2 / 5)
    assert result["toward_turn_fraction"] == pytest.approx(1 / 5)
    assert result["net_away_minus_toward_fraction"] == pytest.approx(1 / 5)
    assert result["away_given_turn_fraction"] == pytest.approx(2 / 3)


def test_danger_right_requires_observed_left_turn_to_count_away() -> None:
    result = summarize_decoded_turns(
        ["TURN_LEFT", "TURN_RIGHT", "TURN_LEFT", "FORWARD"],
        condition="danger_right",
    )
    assert result["expected_away_turn"] == "TURN_LEFT"
    assert result["net_away_minus_toward_fraction"] == pytest.approx(1 / 4)


def test_no_turns_produce_no_conditional_rate() -> None:
    result = summarize_decoded_turns(["FORWARD", "HOLD"], condition="danger_left")
    assert result["turn_fraction"] == 0
    assert result["net_away_minus_toward_fraction"] == 0
    assert result["away_given_turn_fraction"] is None


@pytest.mark.parametrize("condition", ["neutral", "food_left", "food_right"])
def test_control_conditions_do_not_imply_an_avoidance_direction(
    condition: str,
) -> None:
    result = summarize_decoded_turns(["TURN_LEFT", "TURN_RIGHT"], condition=condition)
    assert result["expected_away_turn"] is None
    assert result["net_away_minus_toward_fraction"] is None


def test_empty_and_invalid_actions_are_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        summarize_decoded_turns([], condition="danger_left")
    with pytest.raises(ValueError, match="Unknown decoded"):
        summarize_decoded_turns(["TURN_UP"], condition="danger_left")
    with pytest.raises(ValueError, match="Unsupported"):
        summarize_decoded_turns(["FORWARD"], condition="danger_front")
