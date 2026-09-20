from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_vfb_feco_curated_identity.py")


def load_probe():
    spec = spec_from_file_location("research_probe_vfb_feco_curated_identity", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_targets_curated_r21d12_fanc_identity() -> None:
    probe = load_probe()
    assert probe.FANC_R21D12_TERM == "VFB_001028lx"
    assert probe.FANC_R21D12_NATIVE == "570810"
    assert "R21D12" in probe.SEARCH_QUERIES
    assert probe.FANC_R21D12_PROVENANCE["direct_fanc_em_cell_identity"] is False
    assert probe.FANC_R21D12_PROVENANCE["object_kind"] == "light_microscopy_reference_registered_into_fanc_space"


def test_probe_checks_both_snpp_systematic_types() -> None:
    probe = load_probe()
    assert set(probe.KNOWN_MALECNS_TERMS) == {"SNpp39", "SNpp41"}
    assert probe.KNOWN_MALECNS_TERMS["SNpp41"]["911942"] == "VFB_jrmc173f"
    assert probe.KNOWN_MALECNS_TERMS["SNpp39"]["810041"] == "VFB_jrmc1720"


def test_probe_uses_public_malecns_v1_dvid_annotations() -> None:
    probe = load_probe()
    assert probe.MCNS_DVID_BASE == "https://emdata-mcns.janelia.org"
    assert probe.MCNS_V1_ROOTNODE == "f3969dc575d74e4f922a8966709958c8"
    assert probe.MCNS_ANNOTATION_DATA == "segmentation_annotations"
    assert probe.dvid_annotation_url(911942, "abcdef").endswith(
        "/abcdef/segmentation_annotations/key/911942"
    )


def test_probe_extracts_exact_manc_body_fields() -> None:
    probe = load_probe()
    assert "mancBodyid" in probe.MANC_FIELD_NAMES
    assert "manc_bodyid" in probe.MANC_FIELD_NAMES


def test_probe_is_evidence_only() -> None:
    probe = load_probe()
    assert probe.RECEIPT_SCHEMA == "neurofly-vfb-curated-identity-audit-v0.4"
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"
