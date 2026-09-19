from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_neuronbridge_r21d12.py")


def load_probe():
    spec = spec_from_file_location("research_probe_neuronbridge_r21d12", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_uses_vfb_neuronbridge_accession() -> None:
    probe = load_probe()
    assert probe.SOURCE_DRIVER == "GMR21D12-GAL4"
    assert probe.NEURONBRIDGE_LINE_KEY == "R21D12"
    assert probe.FUNCTIONAL_POLARITY == "hook_flexion"


def test_probe_targets_frozen_malecns_hook_bodies() -> None:
    probe = load_probe()
    assert probe.TARGET_BODIES == {
        "SNpp39": [810041, 813911, 814881, 913886],
        "SNpp41": [819524, 819559, 911942],
    }


def test_probe_is_evidence_only() -> None:
    probe = load_probe()
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"
