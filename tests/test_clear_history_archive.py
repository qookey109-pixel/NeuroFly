from __future__ import annotations

from copy import deepcopy

from neurofly.clear_history import HISTORY_SCHEMA, empty_history, merge_clear_history


def _state(history):
    return {
        "verified": True,
        "backend": "malecns",
        "source_receipt_sha256": "a" * 64,
        "final_state": {"clear_history": history},
    }


def _clear(index: int, *, seconds: float, total_ticks: int):
    return {
        "clear_index": index,
        "episode": index + 2,
        "seconds": seconds,
        "ticks": 100 + index,
        "total_ticks": total_ticks,
        "world_ticks": 200 + index,
        "total_world_ticks": 400 + index,
    }


def test_permanent_clear_history_appends_and_deduplicates() -> None:
    history = empty_history()
    state = _state([
        _clear(1, seconds=12.5, total_ticks=101),
        _clear(2, seconds=10.0, total_ticks=240),
    ])

    merged, added = merge_clear_history(
        history,
        state,
        run_id="1001",
        run_attempt="1",
        recorded_at_utc="2026-09-26T08:00:00Z",
    )

    assert merged["schema"] == HISTORY_SCHEMA
    assert added == 2
    assert merged["total_records"] == 2
    assert [record["history_index"] for record in merged["records"]] == [1, 2]
    assert merged["records"][0]["runtime_clear_index"] == 1

    before = deepcopy(merged)
    merged, added = merge_clear_history(
        merged,
        state,
        run_id="1002",
        run_attempt="1",
        recorded_at_utc="2026-09-26T09:00:00Z",
    )
    assert added == 0
    assert merged == before


def test_permanent_clear_history_never_drops_old_records() -> None:
    history = empty_history()
    history, _ = merge_clear_history(
        history,
        _state([_clear(1, seconds=12.5, total_ticks=101)]),
        run_id="1001",
        run_attempt="1",
        recorded_at_utc="2026-09-26T08:00:00Z",
    )
    first_event_id = history["records"][0]["event_id"]

    history, added = merge_clear_history(
        history,
        _state([
            _clear(1, seconds=12.5, total_ticks=101),
            _clear(2, seconds=9.8, total_ticks=260),
        ]),
        run_id="1002",
        run_attempt="1",
        recorded_at_utc="2026-09-26T09:00:00Z",
    )

    assert added == 1
    assert history["total_records"] == 2
    assert history["records"][0]["event_id"] == first_event_id
    assert history["records"][1]["history_index"] == 2


def test_same_runtime_index_after_reset_is_still_a_new_clear() -> None:
    history = empty_history()
    history, _ = merge_clear_history(
        history,
        _state([_clear(1, seconds=12.5, total_ticks=101)]),
        run_id="1001",
        run_attempt="1",
        recorded_at_utc="2026-09-26T08:00:00Z",
    )

    history, added = merge_clear_history(
        history,
        _state([_clear(1, seconds=8.2, total_ticks=77)]),
        run_id="2001",
        run_attempt="1",
        recorded_at_utc="2026-10-01T08:00:00Z",
    )

    assert added == 1
    assert history["total_records"] == 2
    assert history["records"][0]["runtime_clear_index"] == 1
    assert history["records"][1]["runtime_clear_index"] == 1
    assert history["records"][0]["event_id"] != history["records"][1]["event_id"]
