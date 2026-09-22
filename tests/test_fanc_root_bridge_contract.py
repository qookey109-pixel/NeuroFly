from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_fanc_root_bridge.py")


def load_probe():
    spec = spec_from_file_location("research_probe_fanc_root_bridge", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_pins_public_fanc_sources() -> None:
    probe = load_probe()
    assert probe.GRIDTAPE_REPO == "htem/GridTape_VNC_paper"
    assert probe.GRIDTAPE_COMMIT == "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
    assert probe.FANCR_REPO == "flyconnectome/fancr"
    assert probe.FANCR_COMMIT == "7b3d429729627d83dad9387f54294272640e87f9"


def test_probe_targets_exact_author_top5() -> None:
    probe = load_probe()
    assert list(probe.TARGETS) == [25849, 25842, 25856, 24831, 25909]
    assert probe.TARGETS[25849]["rank"] == 1
    assert probe.TARGETS[25849]["author_nblast_score"] == 0.508957


def test_probe_pins_fancr_canaries() -> None:
    probe = load_probe()
    assert probe.CANARY_EXPECTED_SVID == "73186243730767724"
    assert probe.CANARY_EXPECTED_ROOT == "648518346499897667"
    assert probe.CANARY_FANC4_RAW == (34495.0, 82783.0, 1954.0)
    assert probe.CANARY_EXPECTED_FANC4_RAW == (45224.0, 109317.0, 2614.0)


def test_probe_keeps_downstream_target_frozen() -> None:
    probe = load_probe()
    assert probe.KNOWN_MALECNS_BODY == 911942
    assert probe.KNOWN_MANC_BODY == 97015
    assert probe.KNOWN_MANC_TYPE == "SNpp41"


def test_probe_is_evidence_only() -> None:
    probe = load_probe()
    assert probe.RECEIPT_SCHEMA == "neurofly-fanc-root-bridge-audit-v0.1"
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"


def test_exact_token_guard_does_not_match_substrings() -> None:
    probe = load_probe()
    tsv = "a\tb\t25856\nfoo\t125856\tbar\n"
    hits = probe.exact_token_hits(tsv, {"25856"})
    assert len(hits["25856"]) == 1
    assert "\t25856" in hits["25856"][0]
