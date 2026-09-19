from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_neuronbridge_feco.py")


def load_probe():
    spec = spec_from_file_location("research_probe_neuronbridge_feco", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_is_evidence_only_and_does_not_auto_unlock() -> None:
    probe = load_probe()
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"


def test_probe_targets_cross_version_stable_snpp_bodies() -> None:
    probe = load_probe()
    assert probe.TARGET_BODIES == {
        "SNpp39": [810041, 813911, 814881, 913886],
        "SNpp41": [819524, 819559, 911942],
    }


def test_probe_covers_both_directional_driver_groups() -> None:
    probe = load_probe()
    assert {"VT018774", "VT040547"} <= set(probe.DRIVER_GROUPS["hook_extension"])
    assert {"VT038873", "R32H08", "GMR21D12"} <= set(
        probe.DRIVER_GROUPS["hook_flexion"]
    )
