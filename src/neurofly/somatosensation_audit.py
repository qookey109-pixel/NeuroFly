from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-somatosensation-annotation-audit-v1"
TARGET_CLASS_BY_MODALITY = {
    "tactile": "mechanosensory_tactile",
    "proprioception": "mechanosensory_proprioceptive",
}
CONTEXT_ONLY_CLASSES = {"mechanosensory"}


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


def _counter_map() -> dict[str, Counter[str]]:
    return {name: Counter() for name in TARGET_CLASS_BY_MODALITY}


def audit_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Audit exact curator-labelled tactile/proprioceptive sensory classes read-only.

    Membership is created only by an exact curator annotation class. Words such as
    bristle, chordotonal, campaniform, claw, hook or club are descriptive metadata
    and cannot promote another neuron into either target population. The broad
    ``mechanosensory`` class is reported as context only so existing head/antennal
    mechanosensory populations cannot be silently mixed into this new pathway.
    """

    scanned = 0
    modality_counts: Counter[str] = Counter()
    subclass_counts = _counter_map()
    nerve_counts = _counter_map()
    type_counts = _counter_map()
    instance_counts = _counter_map()
    soma_side_counts = _counter_map()
    superclass_counts = _counter_map()
    descriptive_token_counts = _counter_map()
    context_only_class_counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, str]]] = {
        name: [] for name in TARGET_CLASS_BY_MODALITY
    }

    tokens = (
        "bristle",
        "chordotonal",
        "campaniform",
        "hair plate",
        "feco",
        "club",
        "claw",
        "hook",
        "proprio",
        "tactile",
    )

    class_to_modality = {
        target_class.lower(): modality
        for modality, target_class in TARGET_CLASS_BY_MODALITY.items()
    }

    for raw in records:
        scanned += 1
        neuron_class = _field(raw, "class", "cellClass", "cell_class")
        normalized_class = neuron_class.lower()

        if normalized_class in CONTEXT_ONLY_CLASSES:
            context_only_class_counts[normalized_class] += 1

        modality = class_to_modality.get(normalized_class)
        if modality is None:
            continue

        modality_counts[modality] += 1
        subclass = _field(raw, "subclass", "sub_class")
        nerve = _field(raw, "nerve", "nerveName", "nerve_name")
        neuron_type = _field(raw, "type")
        instance = _field(raw, "instance")
        soma_side = _field(raw, "somaSide", "soma_side").upper()
        superclass = _field(raw, "superclass", "super_class")

        if subclass:
            subclass_counts[modality][subclass] += 1
        if nerve:
            nerve_counts[modality][nerve] += 1
        if neuron_type:
            type_counts[modality][neuron_type] += 1
        if instance:
            instance_counts[modality][instance] += 1
        if soma_side:
            soma_side_counts[modality][soma_side] += 1
        if superclass:
            superclass_counts[modality][superclass] += 1

        searchable = " ".join(
            part for part in (subclass, nerve, neuron_type, instance, superclass) if part
        ).lower()
        for token in tokens:
            if token in searchable:
                descriptive_token_counts[modality][token] += 1

        if len(examples[modality]) < 24:
            examples[modality].append(
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

    tactile = int(modality_counts["tactile"])
    proprioception = int(modality_counts["proprioception"])
    passed = tactile > 0 and proprioception > 0

    def sorted_nested(source: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
        return {
            modality: dict(sorted(source[modality].items()))
            for modality in TARGET_CLASS_BY_MODALITY
        }

    return {
        "schema": AUDIT_SCHEMA,
        "records_scanned": scanned,
        "target_classes": dict(TARGET_CLASS_BY_MODALITY),
        "membership_policy": "curated-class-exact-match-only",
        "modality_counts": {
            modality: int(modality_counts[modality])
            for modality in TARGET_CLASS_BY_MODALITY
        },
        "target_neurons_total": tactile + proprioception,
        "context_only_class_counts": dict(sorted(context_only_class_counts.items())),
        "subclass_counts": sorted_nested(subclass_counts),
        "nerve_counts": sorted_nested(nerve_counts),
        "type_counts": sorted_nested(type_counts),
        "instance_counts": sorted_nested(instance_counts),
        "soma_side_counts": sorted_nested(soma_side_counts),
        "superclass_counts": sorted_nested(superclass_counts),
        "descriptive_token_counts": sorted_nested(descriptive_token_counts),
        "examples": examples,
        "passed": passed,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "existing_jo_ce_routing_modified": False,
        "gates": {
            "curated_tactile_class_present": tactile > 0,
            "curated_proprioceptive_class_present": proprioception > 0,
            "broad_mechanosensory_class_is_context_only": True,
            "stimulation_remains_disabled": True,
        },
        "interpretation": (
            "PASS establishes only that the exact pinned MaleCNS annotations contain "
            "curator-labelled tactile and proprioceptive sensory populations. It does "
            "not assign body-contact geometry, joint state, receptor physiology, "
            "engineering current, or behavioral meaning. Those require separate "
            "crosswalk, transduction, calibration, and runtime gates."
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
            "MaleCNS somatosensation audit requires `.[stonkfly]` and prepared Stonkfly data."
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
        description=(
            "Audit curated MaleCNS tactile/proprioceptive sensory annotations before "
            "somatosensory stimulation"
        )
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/somatosensation-annotation-audit.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
