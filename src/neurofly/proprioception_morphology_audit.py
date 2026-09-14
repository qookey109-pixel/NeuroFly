from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.request
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-proprioception-snpp41-morphology-audit-v1"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
TARGET_CLASS = "mechanosensory_proprioceptive"
TARGET_SUBCLASS = "leg"
PEER_SUBCLASS = "chordotonal organ"
EXPECTED_PEER_COUNT = 21
SWC_BASE_URL = (
    "https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/"
    "skeletons-malecns/skeletons-swc"
)

# Discovery-first by design. The first official-SWC run publishes a deterministic
# morphology receipt and exits non-zero. A later evidence commit may freeze this
# SHA256. Do not guess a morphology threshold or classification here.
EXPECTED_MORPHOLOGY_SHA256: str | None = None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def parse_swc(content: bytes) -> dict[str, Any]:
    """Parse one official MaleCNS SWC and return geometry-only metrics.

    Official MaleCNS SWC coordinates are expressed in 8 nm units. These summary
    metrics are descriptive only; they are not a neuron-classification model.
    """

    nodes: dict[int, tuple[float, float, float, int]] = {}
    children: dict[int, int] = {}
    for raw_line in content.decode("utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 7:
            raise ValueError("Malformed SWC row")
        node_id = int(fields[0])
        x = float(fields[2])
        y = float(fields[3])
        z = float(fields[4])
        parent_id = int(fields[6])
        if node_id in nodes:
            raise ValueError(f"Duplicate SWC node id: {node_id}")
        nodes[node_id] = (x, y, z, parent_id)
        if parent_id >= 0:
            children[parent_id] = children.get(parent_id, 0) + 1

    if not nodes:
        raise ValueError("SWC contains no nodes")

    roots = [node_id for node_id, (_, _, _, parent) in nodes.items() if parent < 0]
    missing_parents = sorted(
        parent
        for _, (_, _, _, parent) in nodes.items()
        if parent >= 0 and parent not in nodes
    )
    if missing_parents:
        raise ValueError(f"SWC references missing parent nodes: {missing_parents[:5]}")

    cable_native = 0.0
    edge_count = 0
    for node_id, (x, y, z, parent) in nodes.items():
        if parent < 0:
            continue
        px, py, pz, _ = nodes[parent]
        cable_native += math.dist((x, y, z), (px, py, pz))
        edge_count += 1

    xs = [row[0] for row in nodes.values()]
    ys = [row[1] for row in nodes.values()]
    zs = [row[2] for row in nodes.values()]
    scale_um = 0.008
    leaves = sum(1 for node_id in nodes if children.get(node_id, 0) == 0)
    branchpoints = sum(1 for count in children.values() if count > 1)

    return {
        "swc_sha256": hashlib.sha256(content).hexdigest(),
        "node_count": len(nodes),
        "edge_count": edge_count,
        "root_count": len(roots),
        "leaf_count": leaves,
        "branchpoint_count": branchpoints,
        "cable_length_um": round(cable_native * scale_um, 6),
        "bbox_span_um": {
            "x": round((max(xs) - min(xs)) * scale_um, 6),
            "y": round((max(ys) - min(ys)) * scale_um, 6),
            "z": round((max(zs) - min(zs)) * scale_um, 6),
        },
    }


def _metric_value(summary: Mapping[str, Any], metric: str) -> float:
    if metric.startswith("bbox_"):
        axis = metric[-1]
        return float(summary["bbox_span_um"][axis])
    return float(summary[metric])


def describe_target_vs_peers(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    target_body_id: str,
    peer_body_ids: Iterable[str],
) -> dict[str, Any]:
    peers = sorted(str(body_id) for body_id in peer_body_ids)
    metrics = (
        "node_count",
        "leaf_count",
        "branchpoint_count",
        "cable_length_um",
        "bbox_x",
        "bbox_y",
        "bbox_z",
    )
    output: dict[str, Any] = {}
    for metric in metrics:
        peer_values = [_metric_value(summaries[body_id], metric) for body_id in peers]
        target_value = _metric_value(summaries[target_body_id], metric)
        percentile = 100.0 * sum(value <= target_value for value in peer_values) / len(peer_values)
        output[metric] = {
            "target": round(target_value, 6),
            "peer_min": round(min(peer_values), 6),
            "peer_median": round(median(peer_values), 6),
            "peer_max": round(max(peer_values), 6),
            "target_percentile": round(percentile, 9),
        }
    return output


def _canonical_receipt(
    *,
    target_body_id: str,
    peer_body_ids: list[str],
    summaries: Mapping[str, Mapping[str, Any]],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source": {
            "release": "MaleCNS v1.0",
            "format": "official centerline SWC",
            "base_url": SWC_BASE_URL,
            "coordinate_units": "8nm",
        },
        "target_body_id": target_body_id,
        "peer_body_ids": sorted(peer_body_ids),
        "skeletons": {
            body_id: summaries[body_id] for body_id in sorted(summaries)
        },
        "comparison": comparison,
    }


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_morphology(
    *,
    target_record: Mapping[str, Any],
    peer_records: Iterable[Mapping[str, Any]],
    summaries: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    target_body_id = _clean(target_record.get("body_id"))
    peers = [dict(row) for row in peer_records]
    peer_body_ids = sorted(_clean(row.get("body_id")) for row in peers)
    expected_ids = {target_body_id, *peer_body_ids}
    comparison = describe_target_vs_peers(
        summaries,
        target_body_id=target_body_id,
        peer_body_ids=peer_body_ids,
    )
    canonical = _canonical_receipt(
        target_body_id=target_body_id,
        peer_body_ids=peer_body_ids,
        summaries=summaries,
        comparison=comparison,
    )
    digest = _sha256_json(canonical)
    frozen = EXPECTED_MORPHOLOGY_SHA256 is not None

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
        "all_skeletons_present": set(summaries) == expected_ids,
        "all_skeletons_nonempty": all(
            int(summary.get("node_count", 0)) > 0 and int(summary.get("edge_count", 0)) > 0
            for summary in summaries.values()
        ),
        "all_raw_swc_sha_present": all(
            len(str(summary.get("swc_sha256", ""))) == 64 for summary in summaries.values()
        ),
    }
    structural_pass = all(structural_gates.values())
    digest_matches = frozen and digest == EXPECTED_MORPHOLOGY_SHA256
    gates = {
        **structural_gates,
        "morphology_receipt_frozen": frozen,
        "morphology_receipt_matches": bool(digest_matches),
        "promotion_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "runtime_transduction_remains_disabled": True,
        "current_calibration_remains_blocked": True,
        "direction_tuning_remains_unresolved": True,
    }
    passed = all(gates.values())
    if passed:
        status = "REVIEW_REQUIRED"
    elif structural_pass and not frozen:
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
            "morphology": summaries[target_body_id],
        },
        "peer_count": len(peers),
        "peer_body_ids": peer_body_ids,
        "comparison": comparison,
        "morphology_sha256": digest,
        "expected_morphology_sha256": EXPECTED_MORPHOLOGY_SHA256,
        "receipt_frozen": frozen,
        "official_swc_source_present": structural_gates["all_skeletons_present"],
        "morphology_evidence_present": structural_gates["all_skeletons_present"],
        "promotion_ready": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "current_calibration_authorized": False,
        "direction_tuning_resolved": False,
        "gates": gates,
        "interpretation": (
            "This receipt is independent centerline-skeleton evidence from the official MaleCNS v1.0 "
            "SWC release. Summary metrics are descriptive only. DISCOVERY_REQUIRED intentionally uses "
            "no post-hoc morphology threshold, does not classify body 905407 as hook/non-hook, and does "
            "not authorize extension/flexion tuning, current calibration, stimulation, or promotion."
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


def _download_swc(body_id: str, *, timeout: float = 30.0) -> bytes:
    url = f"{SWC_BASE_URL}/{body_id}.swc"
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroFly-evidence-audit/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    if not content:
        raise RuntimeError(f"Empty official SWC for body {body_id}")
    return content


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    try:
        import numpy as np
        import pyarrow.feather as feather
        from stonkfly.neural.common import DATA
    except Exception as exc:  # pragma: no cover - prepared runtime only
        raise RuntimeError(
            "SNpp41 morphology audit requires `.[stonkfly]` and prepared MaleCNS annotations"
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

    selected = [TARGET_BODY_ID, *sorted(row["body_id"] for row in peer_records)]
    summaries: dict[str, dict[str, Any]] = {}
    for body_id in selected:
        summaries[body_id] = parse_swc(_download_swc(body_id))

    result = audit_morphology(
        target_record=target_record,
        peer_records=peer_records,
        summaries=summaries,
    )
    result["retained_neurons"] = int(len(ids))
    result["stonkfly_commit"] = STONKFLY_COMMIT
    result["skeleton_source"] = f"{SWC_BASE_URL}/{{bodyId}}.swc"

    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".partial")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover/freeze official MaleCNS SWC morphology for SNpp41 body 905407"
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/snpp41-body905407-morphology-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
