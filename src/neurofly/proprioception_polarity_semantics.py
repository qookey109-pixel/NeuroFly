from __future__ import annotations

from typing import Any, Mapping


SEMANTIC_CONTRACT_SCHEMA = "neurofly-proprioception-systematic-type-semantics-v0.1"
EVIDENCE_SCHEMA = "neurofly-proprioception-hook-direction-evidence-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
EVIDENCE_LEVEL = "PHYSIOLOGY_SUPPORTED_INFERENCE"

_EXPECTED = {
    "SNpp39": ("hook_direction_channel_A", "extension", "hook_extension_sensitive"),
    "SNpp41": ("hook_direction_channel_B", "flexion", "hook_flexion_sensitive"),
}


def build_systematic_type_semantic_contract(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Build a control-plane-only view of unresolved FeCO hook type semantics.

    The virtual body already emits engineering receptor channels named
    ``hook_extension`` and ``hook_flexion``. Those names describe the sign of the
    private virtual joint displacement only. They are not an authorization to
    bind either channel to MaleCNS systematic types SNpp39 or SNpp41.

    This contract preserves the strongest current hypotheses while making them
    explicitly non-authoritative and non-routable.
    """

    if evidence.get("schema") != EVIDENCE_SCHEMA:
        raise ValueError("Unexpected hook direction evidence schema")
    if evidence.get("status") != STATUS_REVIEW:
        raise ValueError("Hook direction evidence must remain REVIEW_REQUIRED")
    if evidence.get("direct_crosswalk_found") is not False:
        raise ValueError("v0.1 semantic firewall requires the direct crosswalk to remain absent")

    for lock in (
        "current_calibration_authorized",
        "stimulation_enabled",
        "runtime_transduction_enabled",
        "promotion_ready",
    ):
        if evidence.get(lock) is not False:
            raise ValueError(f"Hook direction evidence lock opened unexpectedly: {lock}")

    types = evidence.get("systematic_types")
    if not isinstance(types, Mapping) or set(types) != set(_EXPECTED):
        raise ValueError("Expected exactly SNpp39 and SNpp41 hook evidence")

    opaque: dict[str, dict[str, Any]] = {}
    for systematic_type, (opaque_name, expected_hypothesis, candidate_function) in _EXPECTED.items():
        record = types.get(systematic_type)
        if not isinstance(record, Mapping):
            raise ValueError(f"Missing systematic type evidence: {systematic_type}")
        if record.get("anatomical_identity") != "FeCO hook":
            raise ValueError(f"Unexpected anatomical identity: {systematic_type}")
        if record.get("direct_directional_tuning") is not None:
            raise ValueError(
                f"Direct directional tuning cannot be asserted without a frozen crosswalk: {systematic_type}"
            )
        if record.get("circuit_consistent_hypothesis") != expected_hypothesis:
            raise ValueError(f"Unexpected circuit-consistent hypothesis: {systematic_type}")
        if record.get("hypothesis_strength") != "strong-inference-not-direct-crosswalk":
            raise ValueError(f"Systematic type hypothesis must remain explicitly inferential: {systematic_type}")

        opaque[opaque_name] = {
            "systematic_type": systematic_type,
            "anatomical_identity": "FeCO hook",
            "candidate_function": candidate_function,
            "evidence_level": EVIDENCE_LEVEL,
            "authoritative_polarity": False,
            "runtime_routable": False,
        }

    contract = {
        "schema": SEMANTIC_CONTRACT_SCHEMA,
        "status": STATUS_REVIEW,
        "plane": "control-plane-only-not-neural-input",
        "systematic_type_polarity_resolved": False,
        "semantic_polarity": "unresolved",
        "engineering_receptor_channels": {
            "hook_extension": {
                "semantic_scope": "virtual-joint-direction-engineering-proxy",
                "systematic_type_binding": None,
            },
            "hook_flexion": {
                "semantic_scope": "virtual-joint-direction-engineering-proxy",
                "systematic_type_binding": None,
            },
        },
        "opaque_systematic_channels": opaque,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "promotion_ready": False,
        "neural_payload_eligible": False,
    }
    assert_systematic_type_semantic_contract(contract)
    return contract


def assert_systematic_type_semantic_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("schema") != SEMANTIC_CONTRACT_SCHEMA:
        raise ValueError("Unexpected proprioception semantic contract schema")
    if contract.get("status") != STATUS_REVIEW:
        raise ValueError("Proprioception semantic contract must remain REVIEW_REQUIRED")
    if contract.get("plane") != "control-plane-only-not-neural-input":
        raise ValueError("Proprioception semantic contract must remain outside neural input")
    if contract.get("systematic_type_polarity_resolved") is not False:
        raise ValueError("Systematic type polarity must remain unresolved")
    if contract.get("semantic_polarity") != "unresolved":
        raise ValueError("Semantic polarity must remain unresolved")
    if contract.get("neural_payload_eligible") is not False:
        raise ValueError("Semantic contract cannot become neural payload")

    engineering = contract.get("engineering_receptor_channels")
    if not isinstance(engineering, Mapping) or set(engineering) != {"hook_extension", "hook_flexion"}:
        raise ValueError("Unexpected engineering receptor channel set")
    for name in ("hook_extension", "hook_flexion"):
        record = engineering.get(name)
        if not isinstance(record, Mapping):
            raise ValueError(f"Missing engineering receptor channel: {name}")
        if record.get("semantic_scope") != "virtual-joint-direction-engineering-proxy":
            raise ValueError(f"Engineering receptor scope changed: {name}")
        if record.get("systematic_type_binding") is not None:
            raise ValueError(f"Engineering receptor channel cannot bind a systematic type yet: {name}")

    opaque = contract.get("opaque_systematic_channels")
    expected_opaque = {value[0] for value in _EXPECTED.values()}
    if not isinstance(opaque, Mapping) or set(opaque) != expected_opaque:
        raise ValueError("Unexpected opaque systematic channel set")

    for systematic_type, (opaque_name, _, candidate_function) in _EXPECTED.items():
        record = opaque.get(opaque_name)
        if not isinstance(record, Mapping):
            raise ValueError(f"Missing opaque systematic channel: {opaque_name}")
        if record.get("systematic_type") != systematic_type:
            raise ValueError(f"Opaque channel systematic type drift: {opaque_name}")
        if record.get("candidate_function") != candidate_function:
            raise ValueError(f"Candidate function drift: {systematic_type}")
        if record.get("evidence_level") != EVIDENCE_LEVEL:
            raise ValueError(f"Evidence level drift: {systematic_type}")
        if record.get("authoritative_polarity") is not False:
            raise ValueError(f"Candidate polarity cannot become authoritative: {systematic_type}")
        if record.get("runtime_routable") is not False:
            raise ValueError(f"Systematic type channel cannot become runtime-routable: {systematic_type}")

    for lock in (
        "current_calibration_authorized",
        "stimulation_enabled",
        "runtime_transduction_enabled",
        "promotion_ready",
    ):
        if contract.get(lock) is not False:
            raise ValueError(f"Proprioception semantic lock opened unexpectedly: {lock}")


def require_direct_runtime_mapping(contract: Mapping[str, Any]) -> dict[str, str]:
    """Refuse a systematic-type runtime mapping while v0.1 remains unresolved."""

    assert_systematic_type_semantic_contract(contract)
    raise RuntimeError(
        "Direct SNpp39/SNpp41 polarity evidence is required before receptor channels "
        "can bind to systematic types or authorize proprioceptive current"
    )
