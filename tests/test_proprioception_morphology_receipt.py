from __future__ import annotations

import pytest

import neurofly.proprioception_morphology_audit as audit
import neurofly.proprioception_morphology_receipt as receipt


def _verified_result() -> dict:
    return {
        "morphology_sha256": receipt.FROZEN_MORPHOLOGY_SHA256,
        "status": "REVIEW_REQUIRED",
        "passed": True,
        "promotion_ready": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "current_calibration_authorized": False,
        "direction_tuning_resolved": False,
        "target": {
            "morphology": {
                "swc_sha256": receipt.TARGET_RAW_SWC_SHA256,
            }
        },
    }


def test_frozen_receipt_constant_matches_discovery_evidence() -> None:
    assert receipt.FROZEN_MORPHOLOGY_SHA256 == (
        "a0cfd6206b92bb9179eede4c84bfd15da2b284516dfaebeb5e1b6e3c4d37b597"
    )
    assert receipt.TARGET_RAW_SWC_SHA256 == (
        "5934c17b42edc0ea10dc75e571ca258a0321d2b72ecce796f0ee736a606aa174"
    )
    assert receipt.DISCOVERY_RUN_ID == 34813875795


def test_receipt_injects_expected_sha_and_restores_global(monkeypatch) -> None:
    observed = {}

    def fake_run_audit(*, output=None):
        observed["expected"] = audit.EXPECTED_MORPHOLOGY_SHA256
        return _verified_result()

    monkeypatch.setattr(audit, "run_audit", fake_run_audit)
    audit.EXPECTED_MORPHOLOGY_SHA256 = None
    result = receipt.run_frozen_verification()
    assert observed["expected"] == receipt.FROZEN_MORPHOLOGY_SHA256
    assert audit.EXPECTED_MORPHOLOGY_SHA256 is None
    assert result["status"] == "REVIEW_REQUIRED"


def test_receipt_rejects_digest_drift(monkeypatch) -> None:
    result = _verified_result()
    result["morphology_sha256"] = "0" * 64
    monkeypatch.setattr(audit, "run_audit", lambda **kwargs: result)
    with pytest.raises(RuntimeError, match="receipt drifted"):
        receipt.run_frozen_verification()


def test_receipt_rejects_raw_target_swc_drift(monkeypatch) -> None:
    result = _verified_result()
    result["target"]["morphology"]["swc_sha256"] = "1" * 64
    monkeypatch.setattr(audit, "run_audit", lambda **kwargs: result)
    with pytest.raises(RuntimeError, match="raw official SWC digest drifted"):
        receipt.run_frozen_verification()


def test_receipt_never_accepts_current_authorization(monkeypatch) -> None:
    result = _verified_result()
    result["current_calibration_authorized"] = True
    monkeypatch.setattr(audit, "run_audit", lambda **kwargs: result)
    with pytest.raises(RuntimeError, match="must not authorize current calibration"):
        receipt.run_frozen_verification()
