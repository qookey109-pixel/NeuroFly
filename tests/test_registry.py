from neurofly.experiments import list_experiments
from neurofly.upstream import STONKFLY_COMMIT, stonkfly_status


def test_experiment_slugs_are_unique() -> None:
    slugs = [experiment.slug for experiment in list_experiments()]
    assert len(slugs) == len(set(slugs))


def test_initial_playground_contains_stonkfly_replay() -> None:
    assert "stonkfly-replay" in {experiment.slug for experiment in list_experiments()}


def test_stonkfly_upstream_is_pinned() -> None:
    status = stonkfly_status()
    assert status.pinned_commit == STONKFLY_COMMIT
    assert len(status.pinned_commit) == 40
