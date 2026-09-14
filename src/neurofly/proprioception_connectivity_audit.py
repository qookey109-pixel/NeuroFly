from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-proprioception-snpp41-connectivity-audit-v1"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
TARGET_CLASS = "mechanosensory_proprioceptive"
TARGET_SUBCLASS = "leg"
PEER_SUBCLASS = "chordotonal organ"
EXPECTED_PEER_COUNT = 21

# Discovery-first by design. The first prepared run publishes a deterministic
# connectivity receipt and fails. A later evidence commit may freeze its SHA256.
# Do not guess a digest or an interpretation threshold here.
EXPECTED_CONNECTIVITY_SHA256: str | None = None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _taxonomy_label(row: Mapping[str, Any]) -> str:
    for field in ("type", "subclass", "class", "superclass"):
        value = _clean(row.get(field))
        if value:
            return f"{field}:{value}"
    return "unannotated"


def _cosine(left: Mapping[str, int], right: Mapping[str, int]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(float(value) * float(right.get(key, 0)) for key, value in left.items())
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left.values()))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _combined(profile: Mapping[str, Mapping[str, int]]) -> dict[str, int]:
    combined: dict[str, int] = {}
    for direction in ("incoming", "outgoing"):
        for label, count in profile.get(direction, {}).items():
            combined[f"{direction}:{label}"] = int(count)
    return combined


def _top(counter: Mapping[str, int], limit: int = 12) -> list[dict[str, Any]]:
    ordered = sorted(counter.items(), key=lambda item: (-int(item[1]), item[0]))[:limit]
    return [{"partner": key, "contacts": int(value)} for key, value in ordered]


def _profile_summary(profile: Mapping[str, Mapping[str, int]]) -> dict[str, Any]:
    incoming = {str(k): int(v) for k, v in profile.get("incoming", {}).items()}
    outgoing = {str(k): int(v) for k, v in profile.get("outgoing", {}).items()}
    return {
        "incoming_contacts": int(sum(incoming.values())),
        "outgoing_contacts": int(sum(outgoing.values())),
        "incoming_partner_types": len(incoming),
        "outgoing_partner_types": len(outgoing),
        "top_incoming_partner_types": _top(incoming),
        "top_outgoing_partner_types": _top(outgoing),
    }


def _round(value: float) -> float:
    return round(float(value), 9)


def compare_profiles(
    profiles: Mapping[str, Mapping[str, Mapping[str, int]]],
    *,
    target_body_id: str,
    peer_body_ids: Iterable[str],
) -> dict[str, Any]:
    peers = sorted(str(body_id) for body_id in peer_body_ids)
    target = profiles[target_body_id]
    target_combined = _combined(target)
    target_rows = []
    for body_id in peers:
        peer = profiles[body_id]
        target_rows.append(
            {
                "body_id": body_id,
                "incoming_cosine": _round(
                    _cosine(target.get("incoming", {}), peer.get("incoming", {}))
                ),
                "outgoing_cosine": _round(
                    _cosine(target.get("outgoing", {}), peer.get("outgoing", {}))
                ),
                "combined_cosine": _round(_cosine(target_combined, _combined(peer))),
            }
        )
    target_rows.sort(key=lambda row: (-row["combined_cosine"], row["body_id"]))

    peer_medians: list[dict[str, Any]] = []
    for body_id in peers:
        values = [
            _cosine(_combined(profiles[body_id]), _combined(profiles[other]))
            for other in peers
            if other != body_id
        ]
        peer_medians.append(
            {"body_id": body_id, "median_combined_cosine": _round(median(values))}
        )
    peer_medians.sort(key=lambda row: row["body_id"])

    target_median = median(row["combined_cosine"] for row in target_rows)
    baseline_values = [row["median_combined_cosine"] for row in peer_medians]
    percentile = (
        100.0 * sum(value <= target_median for value in baseline_values) / len(baseline_values)
        if baseline_values
        else 0.0
    )
    return {
        "target_vs_peers": target_rows,
        "target_median_combined_cosine": _round(target_median),
        "peer_leave_one_out_medians": peer_medians,
        "peer_baseline": {
            "minimum_median_combined_cosine": _round(min(baseline_values)),
            "median_median_combined_cosine": _round(median(baseline_values)),
            "maximum_median_combined_cosine": _round(max(baseline_values)),
            "target_percentile_among_peer_medians": _round(percentile),
        },
    }


def _canonical_receipt(
    *,
    target_body_id: str,
    peer_body_ids: list[str],
    profiles: Mapping[str, Mapping[str, Mapping[str, int]]],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "target_body_id": target_body_id,
        "peer_body_ids": sorted(peer_body_ids),
        "profiles": {
            body_id: {
                direction: dict(sorted((str(k), int(v)) for k, v in profile[direction].items()))
                for direction in ("incoming", "outgoing")
            }
            for body_id, profile in sorted(profiles.items())
        },
        "comparison": comparison,
    }


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_profiles(
    *,
    target_record: Mapping[str, Any],
    peer_records: Iterable[Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Mapping[str, int]]],
) -> dict[str, Any]:
    target_body_id = _clean(target_record.get("body_id"))
    peers = [dict(row) for row in peer_records]
    peer_body_ids = sorted(_clean(row.get("body_id")) for row in peers)
    comparison = compare_profiles(
        profiles,
        target_body_id=target_body_id,
        peer_body_ids=peer_body_ids,
    )
    receipt = _canonical_receipt(
        target_body_id=target_body_id,
        peer_body_ids=peer_body_ids,
        profiles=profiles,
        comparison=comparison,
    )
    digest = _sha256_json(receipt)
    digest_frozen = EXPECTED_CONNECTIVITY_SHA256 is not None

    structural_gates = {
        "target_body_matches_frozen_identity": target_body_id == TARGET_BODY_ID,
        "target_type_is_snpp41": _clean(target_record.get("type")) == TARGET_TYPE,
        "target_class_matches": _clean(target_record.get("class")).lower() == TARGET_CLASS,
        "target_subclass_is_leg": _clean(target_record.get("subclass")).lower() == TARGET_SUBCLASS,
        "exact_peer_count": len(peers) == EXPECTED_PEER_COUNT,
        "all_peers_are_snpp41": all(_clean(row.get("type")) == TARGET_TYPE for row in peers),
        "all_peers_match_class": all(
            _clean(row.get("class")).lower() == TARGET_CLASS for row in peers
        ),
        "all_peers_are_chordotonal": all(
            _clean(row.get("subclass")).lower() == PEER_SUBCLASS for row in peers
        ),
        "all_peer_body_ids_present": all(peer_body_ids) and len(set(peer_body_ids)) == len(peer_body_ids),
        "all_profiles_present": set(profiles) == {target_body_id, *peer_body_ids},
    }
    structural_pass = all(structural_gates.values())
    digest_matches = digest_frozen and digest == EXPECTED_CONNECTIVITY_SHA256
    gates = {
        **structural_gates,
        "connectivity_receipt_frozen": digest_frozen,
        "connectivity_receipt_matches": bool(digest_matches),
        "promotion_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "current_calibration_remains_blocked": True,
    }
    passed = all(gates.values())
    if passed:
        status = "REVIEW_REQUIRED"
    elif structural_pass and not digest_frozen:
        status = "DISCOVERY_REQUIRED"
    else:
        status = "FAIL"

    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "passed": passed,
        "target": {
            "body_id": target_body_id,
            "type": _clean(target_record.get("type")),
            "class": _clean(target_record.get("class")).lower(),
            "subclass": _clean(target_record.get("subclass")).lower(),
            "superclass": _clean(target_record.get("superclass")).lower(),
            "instance": _clean(target_record.get("instance")),
            "soma_side": _clean(target_record.get("soma_side")).upper(),
            "connectivity": _profile_summary(profiles[target_body_id]),
        },
        "peer_count": len(peers),
        "peer_body_ids": peer_body_ids,
        "comparison": comparison,
        "connectivity_sha256": digest,
        "expected_connectivity_sha256": EXPECTED_CONNECTIVITY_SHA256,
        "receipt_frozen": digest_frozen,
        "promotion_ready": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "current_calibration_authorized": False,
        "morphology_evidence_present": False,
        "gates": gates,
        "interpretation": (
            "This receipt compares synaptic-contact partner-type fingerprints only. "
            "DISCOVERY_REQUIRED intentionally avoids a post-hoc similarity threshold. "
            "A reproduced digest may support review of connectivity consistency, but it is not "
            "morphology evidence and does not authorize sensory tuning, current calibration, "
            "stimulation, or promotion."
        ),
    }


def _annotation_record(body_id: Any, row: Mapping[str, Any]) -> dict[str, str]:
    return {
        "body_id": _clean(body_id),
        "instance": _clean(row.get("instance")),
        "type": _clean(row.get("type")),
        "class": _clean(row.get("class")).lower(),
        "subclass": _clean(row.get("subclass")).lower(),
        "superclass": _clean(row.get("superclass")).lower(),
        "soma_side": _clean(row.get("somaSide")).upper(),
    }


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    try:
        import numpy as np
        import pyarrow as pa
        import pyarrow.feather as feather
        import pyarrow.ipc as ipc
        from stonkfly.neural.common import DATA
    except Exception as exc:  # pragma: no cover - prepared runtime only
        raise RuntimeError(
            "SNpp41 connectivity audit requires `.[stonkfly]` and prepared MaleCNS data"
        ) from exc

    nodes = feather.read_table(DATA / "normalized/neurons.feather").to_pandas()
    ids = nodes.source_id.to_numpy(dtype=np.int64)
    annotations = (
        feather.read_table(DATA / "annotations.feather")
        .to_pandas()
        .set_index("bodyId")
        .loc[ids]
    )

    target_matches = np.flatnonzero(ids == int(TARGET_BODY_ID))
    if len(target_matches) != 1:
        raise RuntimeError(f"Expected exactly one retained body {TARGET_BODY_ID}")
    target_index = int(target_matches[0])
    target_record = _annotation_record(ids[target_index], annotations.iloc[target_index])

    peer_mask = (
        annotations.type.fillna("").astype(str).eq(TARGET_TYPE)
        & annotations["class"].fillna("").astype(str).str.lower().eq(TARGET_CLASS)
        & annotations.subclass.fillna("").astype(str).str.lower().eq(PEER_SUBCLASS)
    ).to_numpy()
    peer_indices = np.flatnonzero(peer_mask)
    peer_records = [_annotation_record(ids[i], annotations.iloc[i]) for i in peer_indices]

    selected_indices = np.asarray([target_index, *peer_indices.tolist()], dtype=np.int32)
    selected_slots = np.full(len(ids), -1, dtype=np.int16)
    selected_slots[selected_indices] = np.arange(len(selected_indices), dtype=np.int16)
    selected_body_ids = [str(int(ids[i])) for i in selected_indices]
    profiles: dict[str, dict[str, Counter[str]]] = {
        body_id: {"incoming": Counter(), "outgoing": Counter()}
        for body_id in selected_body_ids
    }
    labels = [_taxonomy_label(annotations.iloc[i]) for i in range(len(annotations))]

    edge_table = ipc.open_file(
        pa.memory_map(str(DATA / "normalized/edges.arrow"), "r")
    ).read_all()
    pre = edge_table.column("pre_index").to_numpy(zero_copy_only=False)
    post = edge_table.column("post_index").to_numpy(zero_copy_only=False)
    count = edge_table.column("synapse_count").to_numpy(zero_copy_only=False)

    outgoing_mask = selected_slots[pre] >= 0
    for source, partner, contacts in zip(
        pre[outgoing_mask], post[outgoing_mask], count[outgoing_mask]
    ):
        body_id = str(int(ids[int(source)]))
        profiles[body_id]["outgoing"][labels[int(partner)]] += int(contacts)

    incoming_mask = selected_slots[post] >= 0
    for partner, target, contacts in zip(
        pre[incoming_mask], post[incoming_mask], count[incoming_mask]
    ):
        body_id = str(int(ids[int(target)]))
        profiles[body_id]["incoming"][labels[int(partner)]] += int(contacts)

    result = audit_profiles(
        target_record=target_record,
        peer_records=peer_records,
        profiles=profiles,
    )
    result["retained_neurons"] = int(len(ids))
    result["retained_edge_rows"] = int(len(pre))
    result["retained_synaptic_contacts"] = int(count.sum(dtype=np.uint64))
    result["stonkfly_commit"] = STONKFLY_COMMIT
    result["contact_source"] = "normalized/edges.arrow synapse_count"

    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".partial")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover/freeze the MaleCNS connectivity fingerprint of SNpp41 body 905407"
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/snpp41-body905407-connectivity-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
