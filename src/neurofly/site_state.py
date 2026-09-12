from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

from .curriculum import CURRICULUM_VERSION, STAGES
from .olfaction import DANGER_ORN_TYPE, FOOD_ORN_TYPE, OLFACTION_MODEL
from .upstream import STONKFLY_COMMIT


VALID_ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}
VALID_RECEIPT_SCHEMAS = {
    "neurofly-real-smoke-v2",
    "neurofly-self-training-v1",
    "neurofly-self-training-v2",
    "neurofly-self-training-v3",
}
SELF_TRAINING_SCHEMAS = {
    "neurofly-self-training-v1",
    "neurofly-self-training-v2",
    "neurofly-self-training-v3",
}


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _verify_v3_olfaction(receipt: dict[str, Any], trajectory: list[dict[str, Any]]) -> None:
    if receipt.get("olfaction_model") != OLFACTION_MODEL:
        raise ValueError("Self-training v3 does not certify the NeuroFly olfaction model")
    report = receipt.get("olfaction") or {}
    if report.get("model") != OLFACTION_MODEL or report.get("engineered_proxy") is not True:
        raise ValueError("Self-training v3 lacks an olfaction mapping report")

    food = report.get("food") or {}
    danger = report.get("danger") or {}
    if food.get("orn_type") != FOOD_ORN_TYPE or danger.get("orn_type") != DANGER_ORN_TYPE:
        raise ValueError("Self-training v3 olfactory ORN types do not match the V0.6 contract")
    for label, channel in (("food", food), ("danger", danger)):
        try:
            left = int(channel.get("left_neurons", 0))
            right = int(channel.get("right_neurons", 0))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Self-training v3 {label} ORN counts are invalid") from exc
        if left <= 0 or right <= 0:
            raise ValueError(f"Self-training v3 {label} ORNs are not bilateral")

    for index, state in enumerate(trajectory, start=1):
        odor = state.get("olfaction") or {}
        telemetry = ((state.get("brain") or {}).get("telemetry") or {})
        if odor.get("model") != OLFACTION_MODEL:
            raise ValueError(f"Trajectory state {index} lacks the verified odor field")
        if telemetry.get("olfaction_model") != OLFACTION_MODEL:
            raise ValueError(f"Trajectory state {index} lacks MaleCNS olfactory telemetry")
        try:
            food_spikes = int(telemetry.get("food_odor_spikes", -1))
            danger_spikes = int(telemetry.get("danger_odor_spikes", -1))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Trajectory state {index} has invalid olfactory spike telemetry") from exc
        if food_spikes < 0 or danger_spikes < 0:
            raise ValueError(f"Trajectory state {index} lacks olfactory spike telemetry")


def verify_receipt(receipt: dict[str, Any]) -> None:
    supplied_digest = receipt.get("receipt_sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise ValueError("Receipt SHA-256 is missing or malformed")

    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if _digest_json(unsigned) != supplied_digest:
        raise ValueError("Receipt SHA-256 does not match receipt contents")

    schema = receipt.get("schema")
    if schema not in VALID_RECEIPT_SCHEMAS:
        raise ValueError("Unsupported MaleCNS receipt schema")
    if receipt.get("passed") is not True:
        raise ValueError("Real MaleCNS run did not pass")
    if receipt.get("backend") != "malecns":
        raise ValueError("Receipt backend is not MaleCNS")
    if receipt.get("neural_activity_verified") is not True:
        raise ValueError("Receipt does not certify neural activity")
    if receipt.get("stonkfly_commit") != STONKFLY_COMMIT:
        raise ValueError("Receipt Stonkfly revision does not match the NeuroFly pin")

    trajectory = receipt.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        raise ValueError("Receipt does not contain a MaleCNS trajectory")

    for index, state in enumerate(trajectory, start=1):
        if not isinstance(state, dict):
            raise ValueError(f"Trajectory state {index} is not an object")
        brain = state.get("brain") or {}
        telemetry = brain.get("telemetry") or {}
        if brain.get("backend") != "malecns":
            raise ValueError(f"Trajectory state {index} is not MaleCNS")
        if state.get("last_action") not in VALID_ACTIONS:
            raise ValueError(f"Trajectory state {index} has an invalid action")
        try:
            brain_ms = float(telemetry.get("brain_ms"))
            total_spikes = int(telemetry.get("total_spikes"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Trajectory state {index} lacks neural telemetry") from exc
        if not math.isfinite(brain_ms) or brain_ms <= 0 or total_spikes <= 0:
            raise ValueError(f"Trajectory state {index} lacks verifiable neural activity")

    if schema in SELF_TRAINING_SCHEMAS:
        if receipt.get("goal") != "maze_cleared":
            raise ValueError("Self-training receipt has the wrong goal")
        final_state = receipt.get("final_state") or {}
        if final_state.get("goal") != "maze_cleared":
            raise ValueError("Self-training final state does not certify the clear goal")

    if schema in {"neurofly-self-training-v2", "neurofly-self-training-v3"}:
        try:
            world_tick_seconds = float(receipt.get("world_tick_seconds"))
            world_states_seen = int(receipt.get("world_states_seen", 0))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Self-training receipt lacks world-clock evidence") from exc
        if not math.isfinite(world_tick_seconds) or world_tick_seconds <= 0:
            raise ValueError("Self-training receipt has an invalid world tick interval")
        if world_states_seen < 0:
            raise ValueError("Self-training receipt has an invalid world-state count")

    if schema == "neurofly-self-training-v3":
        if receipt.get("curriculum") is not True:
            raise ValueError("Self-training v3 must explicitly enable curriculum")
        if receipt.get("curriculum_version") != CURRICULUM_VERSION:
            raise ValueError("Self-training v3 curriculum version is not recognized")
        final_state = receipt.get("final_state") or {}
        if final_state.get("curriculum_version") != CURRICULUM_VERSION:
            raise ValueError("Final state does not certify the curriculum version")
        try:
            stage = int(final_state.get("curriculum_stage"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Final state lacks a valid curriculum stage") from exc
        if not 1 <= stage <= len(STAGES):
            raise ValueError("Final state curriculum stage is out of range")
        _verify_v3_olfaction(receipt, trajectory)


def build_site_state(receipt: dict[str, Any]) -> dict[str, Any]:
    verify_receipt(receipt)
    return {
        "schema": "neurofly-malecns-site-state-v1",
        "verified": True,
        "backend": "malecns",
        "mode": "recorded-malecns",
        "generated_unix": time.time(),
        "source_receipt_schema": receipt["schema"],
        "source_receipt_sha256": receipt["receipt_sha256"],
        "stonkfly_commit": receipt["stonkfly_commit"],
        "goal": receipt.get("goal"),
        "reward_policy": receipt.get("reward_policy"),
        "world_tick_seconds": receipt.get("world_tick_seconds"),
        "world_states_seen": receipt.get("world_states_seen"),
        "curriculum": receipt.get("curriculum"),
        "curriculum_version": receipt.get("curriculum_version"),
        "olfaction_model": receipt.get("olfaction_model"),
        "olfaction": receipt.get("olfaction"),
        "steps": receipt["steps"],
        "trajectory": receipt["trajectory"],
        "final_state": receipt["final_state"],
    }


def publish_site_state(
    *,
    receipt_path: str | Path,
    output_path: str | Path = "site/malecns-state.json",
) -> dict[str, Any]:
    receipt_path = Path(receipt_path)
    output_path = Path(output_path)
    receipt = json.loads(receipt_path.read_text())
    if not isinstance(receipt, dict):
        raise ValueError("Receipt must be a JSON object")
    state = build_site_state(receipt)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".partial")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    temporary.replace(output_path)
    return state
