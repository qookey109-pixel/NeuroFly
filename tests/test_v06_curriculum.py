from __future__ import annotations

from neurofly.brain_runtime import (
    WALKING_DECODER,
    WALKING_FORWARD_TYPE,
    WALKING_STEERING_TYPE,
    _distributed_pulse_windows,
    _temporal_food_levels,
    _walking_action,
)
from neurofly.curriculum import (
    ACTION_AUTONOMY_POLICY,
    ANTI_STALL_POLICY,
    ANTI_STALL_STATIONARY_LIMIT,
    CURRICULUM_VERSION,
    STALL_STIMULUS_AFTER,
    STALL_STIMULUS_FREQUENCY_HZ,
    STALL_STIMULUS_INTERVAL,
    STALL_STIMULUS_POLICY,
    STALL_STIMULUS_PULSES_PER_DECISION,
    CurriculumMazeEnvironment,
)
from neurofly.goal_training import GoalMazeEnvironment
from neurofly.olfaction import DANGER_ORN_TYPE, FOOD_ORN_TYPE, OLFACTION_MODEL, virtual_olfaction
from neurofly.site_state import _digest_json, build_site_state
from neurofly.training import _public_goal_state
from neurofly.upstream import STONKFLY_COMMIT


def _make_next_forward_clear(env: CurriculumMazeEnvironment) -> None:
    for y, row in enumerate(env.grid):
        for x, cell in enumerate(row):
            if cell in {".", "o"}:
                env.grid[y][x] = " "
    env.fly["dir"] = "RIGHT"
    target_x = env.fly["x"] + 1
    target_y = env.fly["y"]
    assert env.grid[target_y][target_x] != "#"
    env.grid[target_y][target_x] = "."


def test_curriculum_starts_on_full_canonical_maze_without_predator() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    canonical = GoalMazeEnvironment(seed=109)
    state = env.snapshot()

    assert state["curriculum_version"] == CURRICULUM_VERSION
    assert state["curriculum_stage"] == 1
    assert state["curriculum_stage_name"] == "full-maze-foraging"
    assert state["curriculum_enemy_count"] == 0
    assert state["curriculum_clears_to_advance"] == 2
    assert len(env.enemies) == 0
    assert env.grid == canonical.grid
    assert env.fly == canonical.fly
    assert env.food_left() == canonical.food_left()
    assert env.effective_world_tick_seconds(0.5) == 2.0
    assert state["olfaction"]["model"] == OLFACTION_MODEL
    assert state["olfaction"]["food"]["intensity"] > 0
    assert state["olfaction"]["danger"]["intensity"] == 0
    assert state["anti_stall_policy"] == ANTI_STALL_POLICY
    assert state["action_autonomy_policy"] == ACTION_AUTONOMY_POLICY
    assert state["direct_action_override_enabled"] is False
    assert state["stall_stimulus_frequency_hz"] == STALL_STIMULUS_FREQUENCY_HZ
    assert state["stall_stimulus_pulses_per_decision"] == STALL_STIMULUS_PULSES_PER_DECISION


def test_virtual_odor_field_is_bilateral_and_directional() -> None:
    grid = [[" " for _ in range(7)] for _ in range(7)]
    grid[2][3] = "."
    fly = {"x": 3, "y": 3, "dir": "RIGHT"}
    enemies = [{"x": 3, "y": 4}]

    odor = virtual_olfaction(grid=grid, fly=fly, enemies=enemies)

    # Facing right: north is the fly's left side and south is its right side.
    assert odor["food"]["left"] > odor["food"]["right"]
    assert odor["danger"]["right"] > odor["danger"]["left"]
    assert odor["food"]["orn_type"] == FOOD_ORN_TYPE
    assert odor["danger"]["orn_type"] == DANGER_ORN_TYPE


def test_food_odor_field_aggregates_multiple_sources_without_target_action() -> None:
    fly = {"x": 3, "y": 3, "dir": "UP"}
    one = [[" " for _ in range(7)] for _ in range(7)]
    one[3][4] = "."
    two = [row[:] for row in one]
    two[3][5] = "."

    single = virtual_olfaction(grid=one, fly=fly, enemies=[])["food"]
    multi = virtual_olfaction(grid=two, fly=fly, enemies=[])["food"]

    assert single["source_count"] == 1
    assert multi["source_count"] == 2
    assert multi["aggregation"] == "lp4-all-sources"
    assert multi["intensity"] > single["intensity"]
    assert multi["right"] > multi["left"]
    assert "source" not in multi


def test_temporal_food_gradient_strengthens_rising_and_weakens_falling_odor() -> None:
    rising_left, rising_right, rising_delta, rising_mean = _temporal_food_levels(
        0.20, 0.40, 0.20
    )
    assert rising_delta > 0
    assert abs(rising_mean - 0.30) < 1e-12
    assert rising_left > 0.20
    assert rising_right > 0.40

    falling_left, falling_right, falling_delta, _ = _temporal_food_levels(
        0.20, 0.40, 0.40
    )
    assert falling_delta < 0
    assert falling_left < 0.20
    assert falling_right < 0.40


def test_walking_decoder_holds_only_without_walking_dn_activity() -> None:
    assert _walking_action(
        steering_left_hz=0.0,
        steering_right_hz=0.0,
        forward_hz=0.0,
        walking_spikes=0,
        steering_threshold_hz=2.0,
    ) == "HOLD"


def test_walking_decoder_uses_dna02_difference_for_turning() -> None:
    assert _walking_action(
        steering_left_hz=1.0,
        steering_right_hz=5.0,
        forward_hz=0.0,
        walking_spikes=1,
        steering_threshold_hz=2.0,
    ) == "TURN_RIGHT"
    assert _walking_action(
        steering_left_hz=5.0,
        steering_right_hz=1.0,
        forward_hz=0.0,
        walking_spikes=1,
        steering_threshold_hz=2.0,
    ) == "TURN_LEFT"


def test_walking_decoder_uses_dnp09_or_bilateral_activity_for_forward() -> None:
    assert _walking_action(
        steering_left_hz=0.0,
        steering_right_hz=0.0,
        forward_hz=8.0,
        walking_spikes=1,
        steering_threshold_hz=2.0,
    ) == "FORWARD"
    assert _walking_action(
        steering_left_hz=4.0,
        steering_right_hz=4.5,
        forward_hz=0.0,
        walking_spikes=2,
        steering_threshold_hz=2.0,
    ) == "FORWARD"
    assert WALKING_DECODER == "neurofly-walking-decoder-v2"
    assert WALKING_STEERING_TYPE == "DNa02"
    assert WALKING_FORWARD_TYPE == "DNp09"


def test_high_frequency_stall_train_preserves_total_stimulus_budget() -> None:
    windows = _distributed_pulse_windows(
        total_steps=50,
        pulse_budget_steps=20,
        pulse_count=10,
    )

    assert windows == [
        (0, 2),
        (5, 7),
        (10, 12),
        (15, 17),
        (20, 22),
        (25, 27),
        (30, 32),
        (35, 37),
        (40, 42),
        (45, 47),
    ]
    assert len(windows) == 10
    assert sum(end - start for start, end in windows) == 20


def test_sensory_only_autonomy_never_overrides_repeated_hold() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    start = dict(env.fly)

    for _ in range(ANTI_STALL_STATIONARY_LIMIT + 4):
        env.agent_step("HOLD", move_enemies=False)
        state = env.snapshot()
        assert state["raw_brain_action"] == "HOLD"
        assert state["applied_action"] == "HOLD"
        assert state["last_action"] == "HOLD"
        assert state["action_overridden"] is False
        assert state["direct_action_override_enabled"] is False
        assert state["override_reason"] is None
        assert state["anti_stall_force_forward_next"] is False

    assert env.fly == start
    assert env.snapshot()["anti_stall_stationary_steps"] == ANTI_STALL_STATIONARY_LIMIT + 4


def test_repeated_stall_uses_nondirectional_stimulus_without_steering() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    start = dict(env.fly)

    for step in range(1, STALL_STIMULUS_AFTER + 3):
        env.agent_step("HOLD", move_enemies=False)
        expected = "aversive" if step >= STALL_STIMULUS_AFTER else "none"
        assert env.reinforcement() == expected

    state = env.snapshot()
    assert env.fly == start
    assert state["raw_brain_action"] == "HOLD"
    assert state["applied_action"] == "HOLD"
    assert state["action_overridden"] is False
    assert state["override_reason"] is None
    assert state["stall_stimulus_policy"] == STALL_STIMULUS_POLICY
    assert state["stall_stimulus_after"] == STALL_STIMULUS_AFTER
    assert state["stall_stimulus_interval"] == STALL_STIMULUS_INTERVAL

    env.agent_step("TURN_LEFT", move_enemies=False)
    assert env.reinforcement() == "none"
    assert env.snapshot()["anti_stall_stationary_steps"] == 0


def test_sensory_only_autonomy_applies_every_decoded_action_verbatim() -> None:
    env = CurriculumMazeEnvironment(seed=109)

    for action in ("TURN_LEFT", "HOLD", "TURN_RIGHT", "HOLD", "FORWARD", "HOLD"):
        env.agent_step(action, move_enemies=False)
        state = env.snapshot()
        assert state["raw_brain_action"] == action
        assert state["applied_action"] == action
        assert state["last_action"] == action
        assert state["action_overridden"] is False
        assert state["override_reason"] is None
        assert state["direct_action_override_enabled"] is False


def test_stall_observation_state_survives_curriculum_checkpoint() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    env.agent_step("HOLD", move_enemies=False)
    env.agent_step("HOLD", move_enemies=False)
    payload = env.persistence_snapshot()

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)
    state = restored.snapshot()

    assert state["anti_stall_policy"] == ANTI_STALL_POLICY
    assert state["anti_stall_stationary_steps"] == 2
    assert state["raw_brain_action"] == "HOLD"
    assert state["applied_action"] == "HOLD"
    assert state["action_overridden"] is False


def test_two_verified_clears_promote_stage_one_to_full_maze_slow_predator() -> None:
    env = CurriculumMazeEnvironment(seed=109)

    _make_next_forward_clear(env)
    first = env.agent_step("FORWARD", move_enemies=False)
    assert first.event == "maze_cleared"
    env.reset("maze_cleared")
    assert env.curriculum_stage == 1
    assert env.stage_clear_counts["1"] == 1

    _make_next_forward_clear(env)
    second = env.agent_step("FORWARD", move_enemies=False)
    assert second.event == "maze_cleared"
    env.reset("maze_cleared")

    canonical = GoalMazeEnvironment(seed=109)
    assert env.curriculum_stage == 2
    assert env.stage.name == "full-maze-slow-predator"
    assert env.stage_clear_counts["1"] == 2
    assert len(env.enemies) == 1
    assert env.grid == canonical.grid
    assert env.fly == canonical.fly
    assert len(env.stage_history) == 2


def test_predator_pressure_increases_without_changing_maze_geometry() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    canonical = GoalMazeEnvironment(seed=109)

    env.curriculum_stage = 2
    env.reset("test")
    state = env.snapshot()
    assert env.stage.name == "full-maze-slow-predator"
    assert len(env.enemies) == 1
    assert env.effective_world_tick_seconds(0.5) == 2.0
    assert env.grid == canonical.grid
    assert state["olfaction"]["danger"]["intensity"] > 0

    env.curriculum_stage = 3
    env.reset("test")
    assert env.stage.name == "full-maze-predator"
    assert len(env.enemies) == 1
    assert env.effective_world_tick_seconds(0.5) == 1.0
    assert env.grid == canonical.grid

    env.curriculum_stage = 4
    env.reset("test")
    assert env.stage.name == "full-live-maze"
    assert len(env.enemies) == 2
    assert env.effective_world_tick_seconds(9.0) == 0.5
    assert env.grid == canonical.grid


def test_curriculum_checkpoint_preserves_eaten_food() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    baseline_food = env.food_left()
    food_xy = next(
        (x, y)
        for y, row in enumerate(env.grid)
        for x, cell in enumerate(row)
        if cell in {".", "o"}
    )
    x, y = food_xy
    env.grid[y][x] = " "
    payload = env.persistence_snapshot()

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)

    assert restored.curriculum_stage == 1
    assert restored.grid[y][x] == " "
    assert restored.food_left() == baseline_food - 1
    assert len(restored.enemies) == 0


def test_current_enemy_free_checkpoint_remains_valid_without_resetting_progress() -> None:
    source = CurriculumMazeEnvironment(seed=109)
    source.total_ticks = 77
    source.total_world_ticks = 123
    payload = source.persistence_snapshot()
    payload["enemies"] = []

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)

    assert restored.curriculum_stage == 1
    assert len(restored.enemies) == 0
    assert restored.total_ticks == 77
    assert restored.total_world_ticks == 123


def test_v05_state_migrates_to_full_maze_stage_one_without_erasing_global_totals() -> None:
    old = GoalMazeEnvironment(seed=109)
    old.total_ticks = 17
    old.total_world_ticks = 99
    old.total_food = 3
    payload = old.persistence_snapshot()

    migrated = CurriculumMazeEnvironment(seed=109)
    migrated.restore(payload)

    assert migrated.curriculum_stage == 1
    assert migrated.stage.name == "full-maze-foraging"
    assert len(migrated.enemies) == 0
    assert migrated.grid == old.grid
    assert migrated.food_left() == old.food_left()
    assert migrated.total_ticks == 17
    assert migrated.total_world_ticks == 99
    assert migrated.total_food == 3


def test_v3_checkpoint_migrates_to_v4_without_resetting_episode_progress() -> None:
    source = CurriculumMazeEnvironment(seed=109)
    source.agent_step("FORWARD", move_enemies=False)
    source.agent_step("HOLD", move_enemies=False)
    payload = source.persistence_snapshot()
    payload["curriculum_version"] = "neurofly-curriculum-v3"
    payload["anti_stall_force_forward_next"] = True
    payload["applied_action"] = "FORWARD"
    payload["action_overridden"] = True
    payload["override_reason"] = "anti_stall_hold_forward"

    expected_grid = list(payload["grid"])
    expected_fly = dict(payload["fly"])
    expected_ticks = int(payload["total_ticks"])
    expected_food = int(payload["total_food"])

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)
    state = restored.snapshot()

    assert state["curriculum_version"] == CURRICULUM_VERSION
    assert ["".join(row) for row in restored.grid] == expected_grid
    assert restored.fly == expected_fly
    assert restored.total_ticks == expected_ticks
    assert restored.total_food == expected_food
    assert state["applied_action"] == state["raw_brain_action"]
    assert state["action_overridden"] is False
    assert state["override_reason"] is None
    assert state["anti_stall_force_forward_next"] is False
    assert state["direct_action_override_enabled"] is False


def test_v1_enemy_free_checkpoint_migrates_safely_to_v4_full_maze() -> None:
    source = CurriculumMazeEnvironment(seed=109)
    payload = source.persistence_snapshot()
    payload["curriculum_version"] = "neurofly-curriculum-v1"
    payload["enemies"] = []

    restored = CurriculumMazeEnvironment(seed=109)
    restored.restore(payload)
    canonical = GoalMazeEnvironment(seed=109)

    assert restored.curriculum_stage == 1
    assert restored.stage.name == "full-maze-foraging"
    assert len(restored.enemies) == 0
    assert restored.grid == canonical.grid


def test_public_goal_state_preserves_v4_action_autonomy_evidence() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    env.agent_step("HOLD", move_enemies=False)
    state = env.snapshot()
    state["brain"] = {
        "backend": "malecns",
        "telemetry": {
            "brain_ms": 500.0,
            "total_spikes": 123,
        },
    }

    public = _public_goal_state(state)

    assert public["curriculum_version"] == CURRICULUM_VERSION
    assert public["action_autonomy_policy"] == ACTION_AUTONOMY_POLICY
    assert public["direct_action_override_enabled"] is False
    assert public["stall_stimulus_policy"] == STALL_STIMULUS_POLICY
    assert public["stall_stimulus_after"] == STALL_STIMULUS_AFTER
    assert public["stall_stimulus_interval"] == STALL_STIMULUS_INTERVAL
    assert public["raw_brain_action"] == public["applied_action"]
    assert public["action_overridden"] is False
    assert public["override_reason"] is None


def test_v3_curriculum_receipt_is_verified_for_site_state() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    state = env.snapshot()
    state["last_action"] = "HOLD"
    state["world_tick_seconds"] = 1.0
    state["state_kind"] = "neural_decision"
    state["decision_applied"] = True
    state["brain"] = {
        "backend": "malecns",
        "telemetry": {
            "brain_ms": 500.0,
            "total_spikes": 123,
            "olfaction_model": OLFACTION_MODEL,
            "food_odor_spikes": 11,
            "danger_odor_spikes": 1,
        },
    }
    receipt = {
        "schema": "neurofly-self-training-v3",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
        "goal": "maze_cleared",
        "stonkfly_commit": STONKFLY_COMMIT,
        "steps": 1,
        "world_tick_seconds": 1.0,
        "world_states_seen": 1,
        "curriculum": True,
        "curriculum_version": CURRICULUM_VERSION,
        "olfaction_model": OLFACTION_MODEL,
        "olfaction": {
            "model": OLFACTION_MODEL,
            "engineered_proxy": True,
            "food": {
                "orn_type": FOOD_ORN_TYPE,
                "left_neurons": 1,
                "right_neurons": 1,
            },
            "danger": {
                "orn_type": DANGER_ORN_TYPE,
                "left_neurons": 1,
                "right_neurons": 1,
            },
        },
        "trajectory": [state],
        "final_state": state,
    }
    receipt["receipt_sha256"] = _digest_json(receipt)

    site = build_site_state(receipt)

    assert site["verified"] is True
    assert site["source_receipt_schema"] == "neurofly-self-training-v3"
    assert site["curriculum"] is True
    assert site["curriculum_version"] == CURRICULUM_VERSION
    assert site["olfaction_model"] == OLFACTION_MODEL
    assert site["final_state"]["curriculum_stage"] == 1
