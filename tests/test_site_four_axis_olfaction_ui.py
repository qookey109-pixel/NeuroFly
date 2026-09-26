from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "site" / "app.js"


def test_site_displays_four_axis_food_and_danger_olfaction():
    text = APP.read_text()

    assert "食物嗅覺 前" in text
    assert "olfaction.food_front" in text
    assert "olfaction.food_back" in text
    assert "olfaction.food_left" in text
    assert "olfaction.food_right" in text

    assert "危險嗅覺 前" in text
    assert "olfaction.danger_front" in text
    assert "olfaction.danger_back" in text
    assert "olfaction.danger_left" in text
    assert "olfaction.danger_right" in text
