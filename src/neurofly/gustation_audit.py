from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-gustation-annotation-audit-v1"
TARGET_CLASS = "gustatory"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _field(row: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = _clean(row.get(name))
        if value:
            return value
    return ""


def audit_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Discover curated primary gustatory sensory annotations without guessing types.

    The only inclusion gate is the curator-provided annotation class exactly equal
    to ``gustatory`` (case-insensitive). Terms such as sugar, bitter or receptor
    names are reported only as descriptive metadata; they never create membership.
    This keeps downstream taste-circuit neurons from being mistaken for first-order
    sensory GRNs merely because an alias contains a taste-related word.
    """

    scanned = 0
    matched = 0
    class_counts: Counter[str] = Counter()
    subclass_counts: Counter[str] = Counter()
    nerve_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    instance_counts: Counter[str] = Counter()
    soma_side_counts: Counter[str] = Counter()
    superclass_counts: Counter[str] = Counter()
    receptor_token_counts: Counter[str] = Counter()

    receptor_tokens = (
        "gr5a",
        "gr64",
        "gr66a",
        "ir94e",
        "sugar",
        "sweet",
        "bitter",
        "water",
        "salt",
        "taste",
    )

    examples: list[dict[str, str]] = []
    for raw in records:
        scanned += 1
        neuron_class = _field(raw, "class", "cellClass", "cell_class")
        if neuron_class.lower() != TARGET_CLASS:
            continue

        matched += 1
        class_counts[neuron_class] += 1
        subclass = _field(raw, "subclass", "sub_class")
        nerve = _field(raw, "nerve", "nerveName", "nerve_name")
        neuron_type = _field(raw, "type")
        instance = _field(raw, "instance")
        soma_side = _field(raw, "somaSide", "soma_side").upper()
        superclass = _field(raw, "superclass", "super_class")

        if subclass:
            subclass_counts[subclass] += 1
        if nerve:
            nerve_counts[nerve] += 1
        if neuron_type:
            type_counts[neuron_type] += 1
        if instance:
            instance_counts[instance] += 1
        if soma_side:
            soma_side_counts[soma_side] += 1
        if superclass:
            superclass_counts[superclass] += 1

        searchable = " ".join(
            part for part in (subclass, nerve, neuron_type, instance, superclass) if part
        ).lower()
        for token in receptor_tokens:
            if token in searchable:
                receptor_token_counts[token] += 1

        if len(examples) < 24:
            examples.append(
                {
                    "class": neuron_class,
                    "subclass": subclass,
                    "nerve": nerve,
                    "type": neuron_type,
                    "instance": instance,
                    "soma_side": soma_side,
                    "superclass": superclass,
                }
            )

    passed = matched > 0
    return {
        "schema": AUDIT_SCHEMA,
        "target_class": TARGET_CLASS,
        "records_scanned": scanned,
        "gustatory_neurons": matched,
        "passed": passed,
        "stimulation_enabled": False,
        "membership_policy": "curated-class-exact-match-only",
        "class_counts": dict(sorted(class_counts.items())),
        "subclass_counts": dict(sorted(subclass_counts.items())),
        "nerve_counts": dict(sorted(nerve_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
        "instance_counts": dict(sorted(instance_counts.items())),
        "soma_side_counts": dict(sorted(soma_side_counts.items())),
        "superclass_counts": dict(sorted(superclass_counts.items())),
        "descriptive_token_counts": dict(sorted(receptor_token_counts.items())),
        "examples": examples,
        "gates": {
            "curated_gustatory_class_present": passed,
            "stimulation_remains_disabled": True,
        },
        "interpretation": (
            "PASS establishes only that the exact pinned MaleCNS annotations contain "
            "curator-labelled gustatory sensory neurons. Sugar/bitter/water/low-salt "
            "routing and stimulation require a separate subtype audit and calibration."
        ),
    }


def _records_from_annotations(frame: Any) -> tuple[list[dict[str, Any]], list[str]]:
    wanted = (
        "class",
        "cellClass",
        "cell_class",
        "subclass",
        "sub_class",
        "nerve",
        "nerveName",
        "nerve_name",
        "type",
        "instance",
        "somaSide",
        "soma_side",
        "superclass",
        "super_class",
    )
    available = [name for name in wanted if name in frame.columns]
    records = [
        {name: row.get(name) for name in available}
        for row in frame[available].to_dict(orient="records")
    ]
    return records, available


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    """Audit the exact pinned Stonkfly/MaleCNS annotation table read-only."""

    try:
        from stonkfly.neural.common import annotations
        from stonkfly.neural.visual import VisualMemoryBrain
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(
            "MaleCNS gustation audit requires `.[stonkfly]` and prepared Stonkfly data."
        ) from exc

    brain = VisualMemoryBrain()
    frame = annotations(brain.ids)
    records, available_columns = _records_from_annotations(frame)
    result = audit_records(records)
    result["annotation_columns_used"] = available_columns
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
        description="Audit curated MaleCNS gustatory sensory annotations before taste stimulation"
    )
    parser.add_argument(
        "--output",
        default="runs/gustation/gustation-annotation-audit.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
