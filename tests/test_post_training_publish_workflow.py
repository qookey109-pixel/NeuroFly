from pathlib import Path


WORKFLOW = Path('.github/workflows/post-training-publish.yml')


def test_post_training_publish_is_explicit_and_zero_cost() -> None:
    text = WORKFLOW.read_text()
    assert 'workflows: ["NeuroFly Curriculum Training"]' in text
    assert 'types: [completed]' in text
    assert "workflow_run.conclusion == 'success'" in text
    assert 'runs-on: ubuntu-latest' in text
    assert 'actions: write' in text
    assert 'contents: write' in text
    assert 'git merge-base --is-ancestor' in text
    assert 'Refusing to force-push' in text
    assert 'git push origin "$MAIN_SHA:refs/heads/$MIRROR_BRANCH"' in text
    assert '/actions/workflows/pages.yml/dispatches' in text
    assert '-f ref=main' in text
    assert 'force' not in text.lower().replace('refusing to force-push', '')


def test_post_training_publish_does_not_mutate_brain_or_training() -> None:
    text = WORKFLOW.read_text()
    forbidden = (
        'python -m neurofly.training',
        'brain.npz',
        'self-training-receipt.json',
        'reward',
        'plasticity',
    )
    assert all(token not in text for token in forbidden)
