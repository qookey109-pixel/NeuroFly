from __future__ import annotations

import neurofly.proprioception_connectivity_audit as audit
import neurofly.proprioception_connectivity_receipt as receipt


def test_frozen_receipt_is_exact_discovery_digest() -> None:
    assert receipt.DISCOVERY_RUN_ID == 34809806467
    assert receipt.FROZEN_CONNECTIVITY_SHA256 == (
        "353e2771de973ad638878eac9fb1f76e742f928d2cc638c45f1b50775fce2e0e"
    )


def test_receipt_wrapper_injects_digest_without_leaking(monkeypatch) -> None:
    observed: list[str | None] = []
    monkeypatch.setattr(audit, "EXPECTED_CONNECTIVITY_SHA256", None)

    def fake_run_audit(*, output=None):
        observed.append(audit.EXPECTED_CONNECTIVITY_SHA256)
        return {"passed": True, "output": output}

    monkeypatch.setattr(audit, "run_audit", fake_run_audit)
    report = receipt.run_audit(output="receipt.json")

    assert report["passed"] is True
    assert observed == [receipt.FROZEN_CONNECTIVITY_SHA256]
    assert audit.EXPECTED_CONNECTIVITY_SHA256 is None
