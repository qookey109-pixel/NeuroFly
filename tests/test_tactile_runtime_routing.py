from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurofly.tactile import contact_mechanosensation
from neurofly.tactile_runtime import (
    DEFAULT_CALIBRATION_EVIDENCE,
    DEFAULT_CROSSWALK,
    EXPECTED_TACTILE_NEURONS,
    EXPECTED_TACTILE_TYPE_COUNTS,
    TACTILE_CALIBRATED_CURRENT,
    TACTILE_CALIBRATION_RECEIPT_SHA256,
    TACTILE_RUNTIME_SCHEMA,
    load_and_validate_tactile_runtime_evidence,
    tactile_runtime_stimulation,
    validated_tactile_current,
)


def test_runtime_current_accepts_only_zero_or_frozen_calibration() -> None:
    assert validated_tactile_current(0) == 0.0
    assert validated_tactile_current(8) == TACTILE_CALIBRATED_CURRENT
    assert validated_tactile_current(8.0) == TACTILE_CALIBRATED_CURRENT

    for value in (-1, 2, 6, 7.999, 10, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            validated_tactile_current(value)


def test_versioned_runtime_evidence_binds_exact_population_and_receipt() -> None:
    evidence = load_and_validate_tactile_runtime_evidence()
    assert evidence["schema"] == TACTILE_RUNTIME_SCHEMA
    assert evidence["calibrated_current"] == 8.0
    assert evidence["calibration_receipt_sha256"] == TACTILE_CALIBRATION_RECEIPT_SHA256
    assert evidence["population_count"] == EXPECTED_TACTILE_NEURONS == 590
    assert evidence["type_counts"] == EXPECTED_TACTILE_TYPE_COUNTS
    assert evidence["source_runtime_flag"] is False


def test_calibration_evidence_drift_fails_closed(tmp_path: Path) -> None:
    calibration = json.loads(DEFAULT_CALIBRATION_EVIDENCE.read_text())
    calibration["selected"]["current"] = 10.0
    bad_calibration = tmp_path / "bad-calibration.json"
    bad_calibration.write_text(json.dumps(calibration))

    with pytest.raises(RuntimeError, match="selected current"):
        load_and_validate_tactile_runtime_evidence(
            calibration_path=bad_calibration,
            crosswalk_path=DEFAULT_CROSSWALK,
        )

    calibration = json.loads(DEFAULT_CALIBRATION_EVIDENCE.read_text())
    calibration["selected"]["receipt_sha256"] = "0" * 64
    bad_receipt = tmp_path / "bad-receipt.json"
    bad_receipt.write_text(json.dumps(calibration))

    with pytest.raises(RuntimeError, match="receipt"):
        load_and_validate_tactile_runtime_evidence(
            calibration_path=bad_receipt,
            crosswalk_path=DEFAULT_CROSSWALK,
        )


def test_missing_or_contact_off_payload_never_injects_tactile_current() -> None:
    population = [1, 2, 3]

    pulses, levels = tactile_runtime_stimulation(
        None,
        population=population,
        tactile_current=8.0,
    )
    assert pulses == []
    assert levels["contact"] is False
    assert levels["status"] == "no-tactile-payload"

    pulses, levels = tactile_runtime_stimulation(
        contact_mechanosensation(front=0.0),
        population=population,
        tactile_current=8.0,
    )
    assert pulses == []
    assert levels["available"] is True
    assert levels["contact"] is False
    assert levels["front"] == 0.0
    assert levels["runtime_enabled"] is True


def test_contact_payload_routes_exact_calibrated_current() -> None:
    population = [10, 11, 12]
    pulses, levels = tactile_runtime_stimulation(
        contact_mechanosensation(front=1.0),
        population=population,
        tactile_current=8.0,
    )

    assert len(pulses) == 1
    indices, current = pulses[0]
    assert indices is population
    assert current == 8.0
    assert levels["contact"] is True
    assert levels["front"] == 1.0
    assert levels["external_current"] == 8.0
    assert levels["calibrated_current"] == 8.0


def test_privileged_geometry_is_rejected_before_tactile_routing() -> None:
    payload = contact_mechanosensation(front=1.0)
    payload["source"] = {"x": 4, "y": 7}

    with pytest.raises(ValueError, match="Privileged field"):
        tactile_runtime_stimulation(
            payload,
            population=[1, 2, 3],
            tactile_current=8.0,
        )
