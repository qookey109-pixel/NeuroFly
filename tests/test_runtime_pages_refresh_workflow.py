from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / ".github" / "workflows" / "pages.yml"


def test_pages_refreshes_after_curriculum_runtime_completes():
    text = PAGES.read_text()

    assert "workflow_run:" in text
    assert "NeuroFly Curriculum Training" in text
    assert "- completed" in text
    assert "- main" in text


def test_pages_refresh_always_checks_out_main_authority():
    text = PAGES.read_text()

    checkout = text.index("- name: Checkout main")
    configure = text.index("- name: Configure GitHub Pages")
    checkout_block = text[checkout:configure]

    assert "uses: actions/checkout@v6" in checkout_block
    assert "ref: main" in checkout_block


def test_existing_pages_entrypoints_remain_available():
    text = PAGES.read_text()

    assert "push:" in text
    assert "'site/**'" in text
    assert "'.github/workflows/pages.yml'" in text
    assert "workflow_dispatch:" in text
