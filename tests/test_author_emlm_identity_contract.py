from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_author_emlm_identity.py")


def load_probe():
    spec = spec_from_file_location("research_probe_author_emlm_identity", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_author_artifacts_are_pinned() -> None:
    probe = load_probe()
    assert probe.AUTHOR_REPO == "htem/GridTape_VNC_paper"
    assert probe.AUTHOR_COMMIT == "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
    assert probe.R21D12_ATLAS_SKID == 570806
    assert probe.EXPECTED_TOP5 == [515392, 515366, 515458, 511045, 515617]


def test_probe_targets_linking_annotation_not_order_guessing() -> None:
    probe = load_probe()
    assert probe.CATMAID_PROJECT59 == 59
    assert probe.CATMAID_SOURCE_PROJECT == 2
    assert "LINKED NEURON" in probe.LINK_RE.pattern
    assert "elastic transformation" in probe.LINK_RE.pattern
    assert probe.NAME_SOURCE_RE.search(
        "left T1 leg nerve hook chordotonal sensory neuron (neuron 25849) - elastic transform"
    ).group(1) == "25849"


def test_hook_color_is_author_defined() -> None:
    probe = load_probe()
    assert probe.HOOK_COLOR == "#7e2f8e"


def test_downstream_snpp41_target_is_frozen() -> None:
    probe = load_probe()
    assert probe.TARGET_MALECNS_BODY == 911942
    assert probe.TARGET_MANC_BODY == 97015
    assert probe.TARGET_TYPE == "SNpp41"


def test_probe_never_auto_unlocks() -> None:
    probe = load_probe()
    assert probe.RECEIPT_SCHEMA == "neurofly-author-emlm-identity-audit-v0.3"
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"


def test_author_fanc_annotation_source_is_pinned() -> None:
    probe = load_probe()
    assert probe.FANC_ANNOTATION_PATH.endswith(
        "skeletons_in_FANC_space/sensory_neurons_annotations.json"
    )


def test_fanc_source_record_requires_exact_hook_context() -> None:
    probe = load_probe()
    payload = {
        "left T1 leg nerve hook chordotonal sensory neuron (neuron 25849)": [
            "chordotonal neuron",
            "sensory neuron",
            "left T1 leg nerve",
            "T1 leg hook chordotonal neuron",
        ]
    }
    rec = probe.verify_fanc_source_record(25849, payload)
    assert rec["verified_hook_fanc_record"] is True
    assert rec["matching_record_count"] == 1
