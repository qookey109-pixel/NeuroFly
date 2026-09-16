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
