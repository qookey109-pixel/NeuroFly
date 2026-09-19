from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_neuronbridge_r21d12_reverse.py")


def load_probe():
    spec = spec_from_file_location("research_probe_neuronbridge_r21d12_reverse", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reverse_probe_targets_exact_r21d12_images_from_forward_run() -> None:
    probe = load_probe()
    assert probe.LINE_KEY == "R21D12"
    assert "2749246983674789899" in probe.CANDIDATE_LM_IMAGE_IDS
    assert len(probe.CANDIDATE_LM_IMAGE_IDS) == 8


def test_reverse_probe_keeps_same_frozen_body_set() -> None:
    probe = load_probe()
    assert probe.TARGET_BODIES["SNpp39"] == [810041, 813911, 814881, 913886]
    assert probe.TARGET_BODIES["SNpp41"] == [819524, 819559, 911942]


def test_reverse_probe_is_evidence_only() -> None:
    probe = load_probe()
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"
