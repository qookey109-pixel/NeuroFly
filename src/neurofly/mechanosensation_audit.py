from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .mechanosensation import (
    JO_C_TYPE_PREFIX,
    JO_E_TYPE_PREFIX,
    MECHANOSENSATION_MODEL,
)
from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-mechanosensation-annotation-audit-v1"
SIDE_POLICY = "somaSide_then_curated_instance_suffix"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return "" if text.lower() == "nan" else text


def _side(row: Mapping[str, Any]) -> tuple[str | None, str]:
    """Resolve laterality without geometry or body-id inference."""

    soma_side = _clean(row.get("somaSide")).upper()
    if soma_side in {"L", "R"}:
        return soma_side, "somaSide"

    instance = _clean(row.get("instance"))
    if instance.endswith("_L"):
        return "L", "instance_suffix"
    if instance.endswith("_R"):
        return "R", "instance_suffix"
    return None, "unresolved"


def audit_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Audit candidate wind-sensitive JON groups from annotation records.

    Candidate discovery is deliberately broad at the family level: every
    annotation whose curated ``type`` starts with ``JO-C`` or ``JO-E`` is counted.
    The audit does not claim every subtype has identical physiology. It asks the
    narrower engineering question needed before neural stimulation is enabled:
    do the exact MaleCNS annotations contain resolvable bilateral C and E groups?
    """

    families: dict[str, dict[str, Any]] = {
        "JO-C": {
            "prefix": JO_C_TYPE_PREFIX,
            "total": 0,
            "left": 0,
            "right": 0,
            "unresolved": 0,
            "types": Counter(),
            "side_sources": Counter(),
            "neurotransmitters": Counter(),
        },
        "JO-E": {
            "prefix": JO_E_TYPE_PREFIX,
            "total": 0,
            "left": 0,
            "right": 0,
            "unresolved": 0,
            "types": Counter(),
            "side_sources": Counter(),
            "neurotransmitters": Counter(),
        },
    }

    scanned = 0
    for raw in records:
        scanned += 1
        neuron_type = _clean(raw.get("type"))
        family_name = None
        if neuron_type.startswith(JO_C_TYPE_PREFIX):
            family_name = "JO-C"
        elif neuron_type.startswith(JO_E_TYPE_PREFIX):
            family_name = "JO-E"
        if family_name is None:
            continue

        family = families[family_name]
        family["total"] += 1
        family["types"][neuron_type] += 1

        side, source = _side(raw)
        family["side_sources"][source] += 1
        if side == "L":
            family["left"] += 1
        elif side == "R":
            family["right"] += 1
        else:
            family["unresolved"] += 1

        transmitter = _clean(
            raw.get("predictedNt")
            or raw.get("predicted_nt")
            or raw.get("neurotransmitter")
        )
        if transmitter:
            family["neurotransmitters"][transmitter] += 1

    output_families: dict[str, Any] = {}
    gates: list[dict[str, Any]] = []
    for name, family in families.items():
        total = int(family["total"])
        left = int(family["left"])
        right = int(family["right"])
        unresolved = int(family["unresolved"])
        bilateral = left > 0 and right > 0
        no_unresolved = total > 0 and unresolved == 0
        gate = {
            "family": name,
            "has_candidates": total > 0,
            "left_nonempty": left > 0,
            "right_nonempty": right > 0,
            "bilateral": bilateral,
            "all_candidates_lateralized": no_unresolved,
            "passed": bilateral and no_unresolved,
        }
        gates.append(gate)
        output_families[name] = {
            "prefix": family["prefix"],
            "total": total,
            "left": left,
            "right": right,
            "unresolved": unresolved,
            "types": dict(sorted(family["types"].items())),
            "side_sources": dict(sorted(family["side_sources"].items())),
            "neurotransmitters": dict(sorted(family["neurotransmitters"].items())),
        }

    return {
        "schema": AUDIT_SCHEMA,
        "mechanosensation_model": MECHANOSENSATION_MODEL,
        "side_policy": SIDE_POLICY,
        "records_scanned": scanned,
        "families": output_families,
        "gates": gates,
        "passed": all(gate["passed"] for gate in gates),
        "stimulation_enabled": False,
        "interpretation": (
            "PASS establishes only that candidate JO-C/JO-E MaleCNS annotation "
            "families are present and bilaterally resolvable. It does not validate "
            "the NeuroFly airflow-to-deflection physics or authorize biological claims."
        ),
    }


def _records_from_annotations(frame: Any) -> list[dict[str, Any]]:
    columns = {
        "type",
        "instance",
        "somaSide",
        "predictedNt",
        "predicted_nt",
        "neurotransmitter",
    }
    available = [name for name in columns if name in frame.columns]
    return [
        {name: row.get(name) for name in available}
        for row in frame[available].to_dict(orient="records")
    ]


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    """Audit the exact pinned Stonkfly/MaleCNS annotation table."""

    try:
        from stonkfly.neural.common import annotations
        from stonkfly.neural.visual import VisualMemoryBrain
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(
            "MaleCNS annotation audit requires `.[stonkfly]` and prepared Stonkfly data."
        ) from exc

    brain = VisualMemoryBrain()
    frame = annotations(brain.ids)
    result = audit_records(_records_from_annotations(frame))
    result["stonkfly_commit"] = STONKFLY_COMMIT
    result["retained_neurons"] = int(len(brain.ids))

    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".partial")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit bilateral JO-C/JO-E annotations before mechanosensory stimulation"
    )
    parser.add_argument(
        "--output",
        default="runs/free-malecns/mechanosensation-annotation-audit.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
