from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / ".github" / "workflows" / "full-malecns-free.yml"
WATCHDOG = ROOT / ".github" / "workflows" / "runtime-watchdog.yml"


def test_training_handoff_is_retryable_and_nonfatal_after_checkpoint():
    text = TRAINING.read_text()

    assert "id: continue-runtime" in text
    assert "continue-on-error: true" in text
    assert "for attempt in 1 2 3" in text
    assert "CONTINUOUS_RUNTIME_DISPATCH_OK" in text
    assert "the watchdog will recover the chain" in text
    assert "steps.train.outcome == 'success'" in text
    assert "steps.state-cache.outcome == 'success'" in text


def test_watchdog_runs_periodically_and_honors_runtime_policy():
    text = WATCHDOG.read_text()

    assert 'cron: "7,22,37,52 * * * *"' in text
    assert "neurofly-runtime-watchdog" in text
    assert "neurofly-continuous-runtime-v1" in text
    assert "paid_resources'] is False" in text
    assert "steps.policy.outputs.enabled == 'true'" in text
    assert "inputs[continuous]=true" in text


def test_watchdog_refuses_duplicate_active_runner_and_has_visibility_cooldown():
    text = WATCHDOG.read_text()

    active_check = 'select(.status != "completed")'
    assert active_check in text
    assert 'echo "active=$active" >> "$GITHUB_OUTPUT"' in text
    assert "age_seconds" in text
    assert "cooldown_elapsed" in text
    assert "steps.inspect.outputs.active != '0'" in text
    assert "steps.inspect.outputs.active == '0'" in text
    assert "steps.inspect.outputs.cooldown_elapsed == 'true'" in text

    inspect_position = text.index("Inspect NeuroFly curriculum runners")
    recover_position = text.index("Recover stopped continuous runtime")
    assert inspect_position < recover_position


def test_watchdog_dispatch_retries_and_targets_main_authority():
    text = WATCHDOG.read_text()

    assert "for attempt in 1 2 3" in text
    assert '"/repos/${GITHUB_REPOSITORY}/actions/workflows/full-malecns-free.yml/dispatches"' in text
    assert "-f ref=main" in text
    assert "WATCHDOG_RECOVERY_DISPATCH_OK" in text
    assert "The next scheduled watchdog run will retry" in text
