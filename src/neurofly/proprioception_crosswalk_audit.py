from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-proprioception-feco-functional-crosswalk-audit-v1"
SUPPORTED_CROSSWALK_SCHEMAS = {
    "neurofly-proprioception-feco-functional-crosswalk-v0.1",
    "neurofly-proprioception-feco-functional-crosswalk-v0.2",
}
TARGET_CLASS = "mechanosensory_proprioceptive"
TARGET_SUBCLASS = "chordotonal organ"
DEFAULT_CROSSWALK = Path("data/proprioception_feco_functional_crosswalk_v02.json")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def load_crosswalk(path: str | Path = DEFAULT_CROSSWALK) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema") not in SUPPORTED_CROSSWALK_SCHEMAS:
        raise ValueError("Unsupported FeCO crosswalk schema")
    if payload.get("source_population_class") != TARGET_CLASS:
        raise ValueError("FeCO crosswalk must target mechanosensory_proprioceptive")
    if payload.get("accepted_curator_subclasses") != [TARGET_SUBCLASS]:
        raise ValueError("FeCO crosswalk must accept only chordotonal organ")
    if payload.get("stimulation_enabled") is not False:
        raise ValueError("FeCO discovery must not enable stimulation")
    if payload.get("runtime_transduction_enabled") is not False:
        raise ValueError("FeCO discovery must not enable runtime transduction")

    mappings = payload.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("FeCO crosswalk must contain mappings")
    seen: set[str] = set()
    allowed_functions = {
        "feco_hook_motion_direction_candidate",
        "feco_claw_tibia_position_candidate",
        "feco_club_bidirectional_motion_vibration_candidate",
    }
    for mapping in mappings:
        neuron_type = _clean(mapping.get("male_cns_type"))
        function = _clean(mapping.get("functional_class"))
        if not neuron_type or "," in neuron_type or neuron_type in seen:
            raise ValueError("FeCO mappings require unique exact single MaleCNS types")
        seen.add(neuron_type)
        if function not in allowed_functions:
            raise ValueError(f"Unexpected FeCO functional class: {function}")
        if mapping.get("stimulation_authorized") is not False:
            raise ValueError("FeCO mapping must not authorize stimulation")
        evidence = mapping.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Missing evidence for {neuron_type}")
        for item in evidence:
            if not all(_clean(item.get(key)) for key in ("kind", "url", "claim")):
                raise ValueError(f"Incomplete evidence for {neuron_type}")
    return payload


def audit_records(
    records: Iterable[Mapping[str, Any]],
    crosswalk: Mapping[str, Any],
) -> dict[str, Any]:
    mappings = {
        _clean(item["male_cns_type"]): item for item in crosswalk["mappings"]
    }
    mapped_types = set(mappings)

    scanned = 0
    proprio_total = 0
    chordotonal_total = 0
    selected = 0
    selected_type_counts: Counter[str] = Counter()
    selected_function_counts: Counter[str] = Counter()
    non_proprio_rows: Counter[str] = Counter()
    non_proprio_context: dict[str, Counter[str]] = defaultdict(Counter)
    disallowed_subclasses: Counter[str] = Counter()
    ambiguous_related: Counter[str] = Counter()

    for row in records:
        scanned += 1
        neuron_class = _clean(row.get("class", row.get("cellClass", row.get("cell_class")))).lower()
        subclass = _clean(row.get("subclass", row.get("sub_class"))).lower()
        neuron_type = _clean(row.get("type"))
        superclass = _clean(row.get("superclass", row.get("super_class"))).lower()

        if neuron_class == TARGET_CLASS:
            proprio_total += 1
            if subclass == TARGET_SUBCLASS:
                chordotonal_total += 1

        if neuron_class == TARGET_CLASS and "," in neuron_type:
            parts = {_clean(part) for part in neuron_type.split(",") if _clean(part)}
            if parts & mapped_types:
                ambiguous_related[neuron_type] += 1

        if neuron_type not in mapped_types:
            continue
        if neuron_class != TARGET_CLASS:
            non_proprio_rows[neuron_type] += 1
            non_proprio_context[neuron_type][
                "|".join((neuron_class or "<blank-class>", subclass or "<blank-subclass>", superclass or "<blank-superclass>"))
            ] += 1
            continue
        if subclass != TARGET_SUBCLASS:
            disallowed_subclasses[f"{neuron_type}|{subclass or '<blank>'}"] += 1
            continue

        selected += 1
        selected_type_counts[neuron_type] += 1
        selected_function_counts[_clean(mappings[neuron_type]["functional_class"])] += 1

    missing_types = sorted(mapped_types - set(selected_type_counts))
    unresolved = proprio_total - selected
    gates = {
        "all_crosswalk_types_present": not missing_types,
        "no_same_name_rows_outside_proprioceptive_class": not non_proprio_rows,
        "all_selected_rows_are_chordotonal_organ": not disallowed_subclasses,
        "selected_population_nonempty": selected > 0,
        "ambiguous_combined_labels_remain_unselected": True,
        "unresolved_population_preserved": unresolved >= 0,
        "stimulation_remains_disabled": crosswalk.get("stimulation_enabled") is False,
        "runtime_transduction_remains_disabled": crosswalk.get("runtime_transduction_enabled") is False,
    }

    return {
        "schema": AUDIT_SCHEMA,
        "crosswalk_schema": crosswalk["schema"],
        "policy": crosswalk.get("policy"),
        "records_scanned": scanned,
        "proprioceptive_neurons_total": proprio_total,
        "chordotonal_organ_neurons_total": chordotonal_total,
        "crosswalk_types": sorted(mapped_types),
        "crosswalk_type_count": len(mapped_types),
        "selected_feco_candidates": selected,
        "unresolved_proprioceptive_neurons": unresolved,
        "selected_type_counts": dict(sorted(selected_type_counts.items())),
        "selected_function_counts": dict(sorted(selected_function_counts.items())),
        "missing_crosswalk_types": missing_types,
        "non_proprioceptive_mapped_rows": dict(sorted(non_proprio_rows.items())),
        "non_proprioceptive_name_collision_context": {
            key: dict(sorted(value.items())) for key, value in sorted(non_proprio_context.items())
        },
        "disallowed_subclass_rows": dict(sorted(disallowed_subclasses.items())),
        "ambiguous_related_rows_left_unresolved": dict(sorted(ambiguous_related.items())),
        "gates": gates,
        "passed": all(gates.values()),
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "interpretation": (
            "PASS validates only exact evidence-backed FeCO functional candidates in the pinned MaleCNS annotations. Unsupported FeCO functional classes and all non-selected proprioceptive neurons remain unresolved. No receptor mechanics, joint-state transduction, current amplitude, or runtime proprioception is authorized."
        ),
    }


def _records_from_annotations(frame: Any) -> list[dict[str, Any]]:
    columns = [name for name in ("class", "cellClass", "cell_class", "subclass", "sub_class", "superclass", "super_class", "type", "instance") if name in frame.columns]
    return frame[columns].to_dict(orient="records")


def run_audit(*, crosswalk_path: str | Path = DEFAULT_CROSSWALK, output: str | Path | None = None) -> dict[str, Any]:
    try:
        from stonkfly.neural.common import annotations
        from stonkfly.neural.visual import VisualMemoryBrain
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("FeCO audit requires `.[stonkfly]` and prepared MaleCNS data") from exc

    crosswalk = load_crosswalk(crosswalk_path)
    brain = VisualMemoryBrain()
    frame = annotations(brain.ids)
    result = audit_records(_records_from_annotations(frame), crosswalk)
    result["retained_neurons"] = int(len(brain.ids))
    result["stonkfly_commit"] = STONKFLY_COMMIT
    result["crosswalk_path"] = str(crosswalk_path)
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".partial")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit evidence-backed FeCO proprioceptive types against pinned MaleCNS")
    parser.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    parser.add_argument("--output", default="runs/somatosensation/proprioception-feco-crosswalk-audit.json")
    args = parser.parse_args(argv)
    result = run_audit(crosswalk_path=args.crosswalk, output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
