from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / ".github" / "workflows" / "pages.yml"
RUNTIME = ROOT / ".github" / "workflows" / "full-malecns-free.yml"


def test_pages_keeps_explicit_dispatch_and_push_entrypoints():
    text = PAGES.read_text()

    assert "push:" in text
    assert "'site/**'" in text
    assert "'.github/workflows/pages.yml'" in text
    assert "workflow_dispatch:" in text
    assert "workflow_run:" not in text


def test_pages_refresh_always_checks_out_main_authority():
    text = PAGES.read_text()

    checkout = text.index("- name: Checkout main")
    configure = text.index("- name: Configure GitHub Pages")
    checkout_block = text[checkout:configure]

    assert "uses: actions/checkout@v6" in checkout_block
    assert "ref: main" in checkout_block


def test_runtime_explicitly_dispatches_pages_after_verified_publish():
    text = RUNTIME.read_text()

    publish = text.index("- name: Publish latest verified curriculum trajectory to main")
    refresh = text.index("- name: Refresh GitHub Pages from verified main state")
    dataset = text.index("- name: Check dataset cache size")
    refresh_block = text[refresh:dataset]

    assert publish < refresh < dataset
    assert "steps.publish-state.outcome == 'success'" in refresh_block
    assert "continue-on-error: true" in refresh_block
    assert "GH_TOKEN: ${{ github.token }}" in refresh_block
    assert '"/repos/${GITHUB_REPOSITORY}/actions/workflows/pages.yml/dispatches"' in refresh_block
    assert "-f ref=main" in refresh_block
    assert "for attempt in 1 2 3" in refresh_block
    assert "PAGES_REFRESH_DISPATCH_OK" in refresh_block
    assert "verified state remains safe on main" in refresh_block


def test_runtime_pages_dispatch_failure_is_nonfatal_and_visible():
    text = RUNTIME.read_text()

    assert "- name: Warn if Pages refresh dispatch failed" in text
    assert "steps.refresh-pages.outcome == 'failure'" in text
    assert "The runtime chain may continue." in text


def test_runtime_v4_gate_accepts_predator_free_stage_one_and_sensory_only_actions():
    text = RUNTIME.read_text()

    build = text.index("- name: Build verified curriculum state")
    warn = text.index("- name: Warn if verified curriculum state could not be built")
    build_block = text[build:warn]

    assert "state['curriculum_version'] == 'neurofly-curriculum-v4'" in build_block
    assert "final['curriculum_version'] == 'neurofly-curriculum-v4'" in build_block
    assert "final['curriculum_stage_name'] == 'full-maze-foraging'" in build_block
    assert "if stage == 1:" in build_block
    assert "assert enemies == 0" in build_block
    assert "assert enemies >= 1" in build_block
    assert "neurofly-sensory-only-action-autonomy-v1" in build_block
    assert "direct_action_override_enabled" in build_block
    assert "raw_brain_action" in build_block
    assert "applied_action" in build_block
    assert "action_overridden" in build_block
    assert "override_reason" in build_block
    assert "state['curriculum_version'] == 'neurofly-curriculum-v2'" not in build_block


def test_runtime_refuses_stale_state_publish_when_main_advanced():
    text = RUNTIME.read_text()

    publish = text.index("- name: Publish latest verified curriculum trajectory to main")
    warn = text.index("- name: Warn if verified state could not be published")
    publish_block = text[publish:warn]

    assert 'RUN_SOURCE_SHA="$GITHUB_SHA"' in publish_block
    assert 'CURRENT_AUTHORITY_SHA="$(git rev-parse "origin/$AUTHORITY_BRANCH")"' in publish_block
    assert 'if [ "$CURRENT_AUTHORITY_SHA" != "$RUN_SOURCE_SHA" ]; then' in publish_block
    assert "skip stale verified-state publish" in publish_block
    assert "exit 1" in publish_block
    assert publish_block.index("CURRENT_AUTHORITY_SHA=") < publish_block.index("git checkout -B")


def test_runtime_cancels_stale_code_runs_but_preserves_continuous_handoffs():
    text = RUNTIME.read_text()

    assert "group: neurofly-v06-curriculum-training" in text
    assert "cancel-in-progress: ${{ github.event_name == 'push' }}" in text
    assert '"src/neurofly/**"' in text
    assert '"config/neurofly_continuous_runtime.json"' in text
    assert '"pyproject.toml"' in text
