from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .sensory_contract import assert_unprivileged_agent_input
from .tactile import TACTILE_MODEL, tactile_channel_levels


TACTILE_RUNTIME_SCHEMA = "neurofly-tactile-runtime-routing-v1"
TACTILE_CALIBRATION_SELECTION_SCHEMA = "neurofly-tactile-current-calibration-selection-v1"
TACTILE_CROSSWALK_SCHEMA = "neurofly-tactile-leg-functional-crosswalk-v0.2"
TACTILE_CALIBRATED_CURRENT = 8.0
TACTILE_CALIBRATION_RECEIPT_SHA256 = (
    "41592fd805bbfa19f73959af24479d12770e10866ed05e8fc85a86eac198f462"
)
TACTILE_CROSSWALK_SHA256 = (
    "4cd8a25f2647be6399642a230ee947ce19cf72f5fc22b3e5ad4591eec78ab8cc"
)
TACTILE_BODY_IDS_SHA256 = (
    "007556a35ccfcbf41fac8b00db1f56cfddbe136a0056ed69a1724224289a6395"
)
EXPECTED_TACTILE_TYPE_COUNTS = {
    "SNta20": 156,
    "SNta26": 31,
    "SNta27": 47,
    "SNta28": 74,
    "SNta34": 54,
    "SNta37": 228,
}
EXPECTED_TACTILE_NEURONS = 590
ACCEPTED_TACTILE_SUBCLASSES = {"leg", "mechanosensory bristle"}
DEFAULT_CALIBRATION_EVIDENCE = (
    Path(__file__).resolve().parents[2] / "data" / "tactile_current_calibration_v1.json"
)
DEFAULT_CROSSWALK = (
    Path(__file__).resolve().parents[2] / "data" / "tactile_leg_functional_crosswalk_v02.json"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validated_tactile_current(value: Any) -> float:
    """Accept only zero or the frozen calibrated tactile engineering current."""

    try:
        current = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("tactile_current must be finite") from exc
    if not math.isfinite(current) or current < 0.0:
        raise ValueError("tactile_current must be finite and nonnegative")
    if current == 0.0:
        return 0.0
    if not math.isclose(
        current,
        TACTILE_CALIBRATED_CURRENT,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "tactile_current must be 0.0 (internal compatibility) or the calibrated "
            f"engineering current {TACTILE_CALIBRATED_CURRENT}"
        )
    return TACTILE_CALIBRATED_CURRENT


def load_and_validate_tactile_runtime_evidence(
    *,
    calibration_path: str | Path = DEFAULT_CALIBRATION_EVIDENCE,
    crosswalk_path: str | Path = DEFAULT_CROSSWALK,
) -> dict[str, Any]:
    """Bind runtime routing to the frozen calibration/crosswalk evidence.

    The calibration receipt comes from the permanent source run recorded in the
    repository. Later reproducibility reruns may produce different receipt hashes
    because their receipts include run-local metadata; runtime authorization stays
    bound to the versioned source evidence file instead of silently following the
    newest CI artifact.
    """

    calibration_path = Path(calibration_path)
    crosswalk_path = Path(crosswalk_path)
    calibration = json.loads(calibration_path.read_text())
    crosswalk = json.loads(crosswalk_path.read_text())

    if calibration.get("schema") != TACTILE_CALIBRATION_SELECTION_SCHEMA:
        raise RuntimeError("Unexpected tactile calibration evidence schema")
    if calibration.get("crosswalk_schema") != TACTILE_CROSSWALK_SCHEMA:
        raise RuntimeError("Tactile calibration references an unexpected crosswalk schema")
    if calibration.get("runtime_stimulation_enabled") is not False:
        raise RuntimeError("Source tactile calibration must remain non-runtime evidence")
    if int(calibration.get("population_count", -1)) != EXPECTED_TACTILE_NEURONS:
        raise RuntimeError("Tactile calibration population count drifted")
    if calibration.get("type_counts") != EXPECTED_TACTILE_TYPE_COUNTS:
        raise RuntimeError("Tactile calibration per-type counts drifted")
    if calibration.get("crosswalk_sha256") != TACTILE_CROSSWALK_SHA256:
        raise RuntimeError("Tactile calibration crosswalk digest drifted")
    if calibration.get("selected_body_ids_sha256") != TACTILE_BODY_IDS_SHA256:
        raise RuntimeError("Tactile calibration body-ID digest drifted")

    selected = calibration.get("selected") or {}
    if not math.isclose(
        float(selected.get("current", -1.0)),
        TACTILE_CALIBRATED_CURRENT,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError("Tactile selected current no longer matches runtime constant")
    if selected.get("receipt_sha256") != TACTILE_CALIBRATION_RECEIPT_SHA256:
        raise RuntimeError("Tactile calibration receipt no longer matches frozen runtime evidence")
    population_gate = selected.get("selected_population") or {}
    if population_gate.get("passed") is not True:
        raise RuntimeError("Tactile calibration selected population gate is not PASS")
    if int(population_gate.get("neurons", -1)) != EXPECTED_TACTILE_NEURONS:
        raise RuntimeError("Tactile selected population gate count drifted")
    type_gates = selected.get("type_gates") or {}
    if set(type_gates) != set(EXPECTED_TACTILE_TYPE_COUNTS):
        raise RuntimeError("Tactile calibration type-gate set drifted")
    for neuron_type, expected in EXPECTED_TACTILE_TYPE_COUNTS.items():
        gate = type_gates.get(neuron_type) or {}
        if gate.get("passed") is not True or int(gate.get("neurons", -1)) != expected:
            raise RuntimeError(f"Tactile calibration gate drifted for {neuron_type}")

    if crosswalk.get("schema") != TACTILE_CROSSWALK_SCHEMA:
        raise RuntimeError("Unexpected tactile crosswalk schema")
    if crosswalk.get("source_population_class") != "mechanosensory_tactile":
        raise RuntimeError("Tactile crosswalk source class drifted")
    if crosswalk.get("stimulation_enabled") is not False:
        raise RuntimeError("Tactile crosswalk must remain a non-authorizing anatomy ledger")
    if crosswalk.get("runtime_transduction_enabled") is not False:
        raise RuntimeError("Tactile crosswalk runtime flag must remain false")
    if _sha256_file(crosswalk_path) != TACTILE_CROSSWALK_SHA256:
        raise RuntimeError("Active tactile crosswalk file digest drifted")

    mapped_types = [str(item.get("male_cns_type") or "") for item in crosswalk.get("mappings", [])]
    if set(mapped_types) != set(EXPECTED_TACTILE_TYPE_COUNTS):
        raise RuntimeError("Active tactile crosswalk type set drifted")

    return {
        "schema": TACTILE_RUNTIME_SCHEMA,
        "model": TACTILE_MODEL,
        "calibrated_current": TACTILE_CALIBRATED_CURRENT,
        "calibration_receipt_sha256": TACTILE_CALIBRATION_RECEIPT_SHA256,
        "crosswalk_schema": TACTILE_CROSSWALK_SCHEMA,
        "crosswalk_sha256": TACTILE_CROSSWALK_SHA256,
        "selected_body_ids_sha256": TACTILE_BODY_IDS_SHA256,
        "population_count": EXPECTED_TACTILE_NEURONS,
        "type_counts": dict(EXPECTED_TACTILE_TYPE_COUNTS),
        "source_runtime_flag": False,
        "runtime_authorized_by": "versioned-neurofly-runtime-routing-stage",
    }


def resolve_tactile_runtime_population(
    np: Any,
    annotations: Any,
    body_ids: Any,
) -> tuple[Any, dict[str, Any]]:
    """Resolve exactly the audited 590 tactile candidates and reject drift."""

    if "class" not in annotations.columns or "subclass" not in annotations.columns:
        raise RuntimeError("MaleCNS tactile routing requires class and subclass annotations")

    types = annotations.type.fillna("").astype(str)
    classes = annotations["class"].fillna("").astype(str).str.lower()
    subclasses = annotations["subclass"].fillna("").astype(str).str.lower()
    selected_mask = np.zeros(len(annotations), dtype=bool)
    type_report: dict[str, Any] = {}

    for neuron_type, expected in sorted(EXPECTED_TACTILE_TYPE_COUNTS.items()):
        type_mask = types.eq(neuron_type)
        non_tactile = type_mask & ~classes.eq("mechanosensory_tactile")
        if int(non_tactile.sum()) != 0:
            raise RuntimeError(
                f"Mapped tactile type {neuron_type} has non-tactile rows: {int(non_tactile.sum())}"
            )

        tactile_rows = type_mask & classes.eq("mechanosensory_tactile")
        disallowed = tactile_rows & ~subclasses.isin(ACCEPTED_TACTILE_SUBCLASSES)
        if int(disallowed.sum()) != 0:
            raise RuntimeError(
                f"Mapped tactile type {neuron_type} has disallowed subclasses: {int(disallowed.sum())}"
            )

        indices = np.flatnonzero(tactile_rows.to_numpy())
        if len(indices) != expected:
            raise RuntimeError(
                f"Mapped tactile type {neuron_type} count drifted: expected={expected} actual={len(indices)}"
            )
        selected_mask |= tactile_rows.to_numpy()
        type_report[neuron_type] = {
            "neurons": int(len(indices)),
            "subclasses": sorted(set(subclasses[tactile_rows].tolist())),
        }

    selected = np.flatnonzero(selected_mask)
    if len(selected) != EXPECTED_TACTILE_NEURONS:
        raise RuntimeError(
            f"Mapped tactile population count drifted: expected={EXPECTED_TACTILE_NEURONS} actual={len(selected)}"
        )
    body_digest = hashlib.sha256(body_ids[selected].tobytes()).hexdigest()
    if body_digest != TACTILE_BODY_IDS_SHA256:
        raise RuntimeError("Mapped tactile body-ID digest drifted from calibration evidence")

    return selected, {
        "membership_policy": "six-exact-types-plus-curated-class-subclass-plus-body-id-digest",
        "neurons": int(len(selected)),
        "type_counts": {key: value["neurons"] for key, value in type_report.items()},
        "types": type_report,
        "body_ids_sha256": body_digest,
        "unresolved_tactile_neurons_used": 0,
    }


def tactile_runtime_stimulation(
    payload: dict[str, Any] | None,
    *,
    population: Any,
    tactile_current: float,
) -> tuple[list[tuple[Any, float]], dict[str, Any]]:
    """Translate the strict one-shot contact payload into calibrated current."""

    if not payload:
        return [], {
            "available": False,
            "contact": False,
            "front": 0.0,
            "runtime_enabled": tactile_current > 0.0,
            "external_current": tactile_current,
            "calibrated_current": TACTILE_CALIBRATED_CURRENT,
            "status": "no-tactile-payload",
        }

    assert_unprivileged_agent_input({"contact_mechanosensation": payload})
    levels = tactile_channel_levels(payload)
    levels = {
        **levels,
        "runtime_enabled": tactile_current > 0.0,
        "external_current": tactile_current,
        "calibrated_current": TACTILE_CALIBRATED_CURRENT,
    }
    if (
        not levels.get("available")
        or not levels.get("contact")
        or float(levels.get("front", 0.0)) <= 0.0
        or tactile_current <= 0.0
    ):
        return [], levels

    return [
        (population, tactile_current * float(levels["front"]))
    ], levels
