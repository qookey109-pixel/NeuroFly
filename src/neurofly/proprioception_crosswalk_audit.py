from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-proprioception-feco-functional-crosswalk-audit-v2"
SUPPORTED_CROSSWALK_SCHEMAS = {
    "neurofly-proprioception-feco-functional-crosswalk-v0.1",
    "neurofly-proprioception-feco-functional-crosswalk-v0.2",
    "neurofly-proprioception-feco-functional-crosswalk-v0.3",
}
V03_SCHEMA = "neurofly-proprioception-feco-functional-crosswalk-v0.3"
TARGET_CLASS = "mechanosensory_proprioceptive"
TARGET_SUBCLASS = "chordotonal organ"
HOOK_FUNCTION = "feco_hook_motion_direction_candidate"
EXPECTED_V03_HOOK_TYPES = {"SNpp39", "SNpp41"}
EXPECTED_V03_EXCEPTION = {"SNpp41|leg": 1}
DEFAULT_CROSSWALK = Path("data/proprioception_feco_functional_crosswalk_v03.json")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _v03_expected_exceptions(payload: Mapping[str, Any]) -> dict[str, int]:
    items = payload.get("expected_annotation_exceptions")
    if not isinstance(items, list) or len(items) != 1:
        raise ValueError("FeCO v0.3 requires exactly one pinned annotation exception receipt")
    item = items[0]
    if not isinstance(item, Mapping):
        raise ValueError("FeCO v0.3 annotation exception must be an object")
    neuron_type = _clean(item.get("male_cns_type"))
    neuron_class = _clean(item.get("class")).lower()
    subclass = _clean(item.get("subclass")).lower()
    try:
        count = int(item.get("count", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("FeCO v0.3 annotation exception count must be an integer") from exc
    if (
        neuron_type != "SNpp41"
        or neuron_class != TARGET_CLASS
        or subclass != "leg"
        or count != 1
        or item.get("disposition") != "review_required_not_selected_not_stimulated"
    ):
        raise ValueError("FeCO v0.3 pinned annotation exception receipt drifted")
    return {f"{neuron_type}|{subclass}": count}


def load_crosswalk(path: str | Path = DEFAULT_CROSSWALK) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    schema = payload.get("schema")
    if schema not in SUPPORTED_CROSSWALK_SCHEMAS:
        raise ValueError("Unsupported FeCO crosswalk schema")
    if payload.get("source_population_class") != TARGET_CLASS:
        raise ValueError("FeCO crosswalk must target mechanosensory_proprioceptive")
    if payload.get("accepted_curator_subclasses") != [TARGET_SUBCLASS]:
        raise ValueError("FeCO crosswalk must accept only chordotonal organ")
    if payload.get("stimulation_enabled") is not False:
        raise ValueError("FeCO discovery must not enable stimulation")
    if payload.get("runtime_transduction_enabled") is not False:
        raise ValueError("FeCO discovery must not enable runtime transduction")

    if schema == V03_SCHEMA:
        if payload.get("promotion_status") != "review_required":
            raise ValueError("FeCO v0.3 promotion status must remain review_required")
        if payload.get("promotion_ready") is not False:
            raise ValueError("FeCO v0.3 must not be promotion ready")
        if payload.get("directional_hook_identity_resolved") is not False:
            raise ValueError("FeCO v0.3 must keep directional hook identity unresolved")
        if payload.get("current_calibration_authorized") is not False:
            raise ValueError("FeCO v0.3 must not authorize current calibration")
        _v03_expected_exceptions(payload)

    mappings = payload.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("FeCO crosswalk must contain mappings")
    seen: set[str] = set()
    hook_types: set[str] = set()
    allowed_functions = {
        HOOK_FUNCTION,
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
        if schema == V03_SCHEMA:
            expected_status = (
                "review_required_mixed_subclass"
                if neuron_type == "SNpp41"
                else "clean_candidate"
            )
            if mapping.get("mapping_status") != expected_status:
                raise ValueError(f"FeCO v0.3 mapping status drifted for {neuron_type}")
            if function == HOOK_FUNCTION:
                hook_types.add(neuron_type)
                if mapping.get("hook_direction_identity") != "unresolved":
                    raise ValueError(
                        "FeCO v0.3 hook mappings must keep extension/flexion identity unresolved"
                    )
        evidence = mapping.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Missing evidence for {neuron_type}")
        for item in evidence:
            if not all(_clean(item.get(key)) for key in ("kind", "url", "claim")):
                raise ValueError(f"Incomplete evidence for {neuron_type}")

    if schema == V03_SCHEMA and hook_types != EXPECTED_V03_HOOK_TYPES:
        raise ValueError(
            "FeCO v0.3 must preserve the complete evidence-review SNpp39/SNpp41 hook pair"
        )
    return payload


def audit_records(
    records: Iterable[Mapping[str, Any]],
    crosswalk: Mapping[str, Any],
) -> dict[str, Any]:
    mappings = {
        _clean(item["male_cns_type"]): item for item in crosswalk["mappings"]
    }
    mapped_types = set(mappings)
    is_v03 = crosswalk.get("schema") == V03_SCHEMA

    scanned = 0
    proprio_total = 0
    chordotonal_total = 0
    selected = 0
    selected_type_counts: Counter[str] = Counter()
    selected_function_counts: Counter[str] = Counter()
    selected_mapping_status_counts: Counter[str] = Counter()
    non_proprio_rows: Counter[str] = Counter()
    non_proprio_context: dict[str, Counter[str]] = defaultdict(Counter)
    disallowed_subclasses: Counter[str] = Counter()
    ambiguous_related: Counter[str] = Counter()

    for row in records:
        scanned += 1
        neuron_class = _clean(
            row.get("class", row.get("cellClass", row.get("cell_class")))
        ).lower()
        subclass = _clean(row.get("subclass", row.get("sub_class"))).lower()
        neuron_type = _clean(row.get("type"))
        superclass = _clean(
            row.get("superclass", row.get("super_class"))
        ).lower()

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
                "|".join(
                    (
                        neuron_class or "<blank-class>",
                        subclass or "<blank-subclass>",
                        superclass or "<blank-superclass>",
                    )
                )
            ] += 1
            continue
        if subclass != TARGET_SUBCLASS:
            disallowed_subclasses[f"{neuron_type}|{subclass or '<blank>'}"] += 1
            continue

        selected += 1
        selected_type_counts[neuron_type] += 1
        selected_function_counts[_clean(mappings[neuron_type]["functional_class"])] += 1
        selected_mapping_status_counts[
            _clean(mappings[neuron_type].get("mapping_status", "legacy"))
        ] += 1

    missing_types = sorted(mapped_types - set(selected_type_counts))
    unresolved = proprio_total - selected
    directional_hook_identity_resolved = bool(
        crosswalk.get("directional_hook_identity_resolved", False)
    )
    current_calibration_authorized = bool(
        crosswalk.get("current_calibration_authorized", False)
    )
    hook_types = {
        neuron_type
        for neuron_type, mapping in mappings.items()
        if _clean(mapping.get("functional_class")) == HOOK_FUNCTION
    }
    hook_identity_values = {
        neuron_type: _clean(mappings[neuron_type].get("hook_direction_identity"))
        for neuron_type in sorted(hook_types)
        if "hook_direction_identity" in mappings[neuron_type]
    }

    gates = {
        "all_crosswalk_types_present": not missing_types,
        "no_same_name_rows_outside_proprioceptive_class": not non_proprio_rows,
        "selected_population_nonempty": selected > 0,
        "ambiguous_combined_labels_remain_unselected": True,
        "unresolved_population_preserved": unresolved >= 0,
        "stimulation_remains_disabled": crosswalk.get("stimulation_enabled") is False,
        "runtime_transduction_remains_disabled": crosswalk.get("runtime_transduction_enabled") is False,
    }
    if is_v03:
        expected_exceptions = _v03_expected_exceptions(crosswalk)
        actual_exceptions = dict(sorted(disallowed_subclasses.items()))
        gates.update(
            {
                "annotation_exceptions_match_pinned_receipt": actual_exceptions
                == expected_exceptions,
                "complete_hook_pair_present_for_review": hook_types
                == EXPECTED_V03_HOOK_TYPES,
                "hook_direction_identity_remains_unresolved": (
                    not directional_hook_identity_resolved
                    and hook_identity_values
                    == {"SNpp39": "unresolved", "SNpp41": "unresolved"}
                ),
                "promotion_remains_review_required": (
                    crosswalk.get("promotion_status") == "review_required"
                    and crosswalk.get("promotion_ready") is False
                ),
                "current_calibration_remains_blocked": not current_calibration_authorized,
            }
        )
    else:
        expected_exceptions = {}
        gates["all_mapped_rows_use_allowed_subclass"] = not disallowed_subclasses

    audit_passed = all(gates.values())
    status = (
        "REVIEW_REQUIRED"
        if is_v03 and audit_passed
        else ("PASS" if audit_passed else "FAIL")
    )
    clean_selected = sum(
        count
        for neuron_type, count in selected_type_counts.items()
        if _clean(mappings[neuron_type].get("mapping_status")) == "clean_candidate"
    )
    review_selected = sum(
        count
        for neuron_type, count in selected_type_counts.items()
        if _clean(mappings[neuron_type].get("mapping_status")).startswith("review_required")
    )

    return {
        "schema": AUDIT_SCHEMA,
        "crosswalk_schema": crosswalk["schema"],
        "policy": crosswalk.get("policy"),
        "status": status,
        "promotion_status": crosswalk.get("promotion_status"),
        "promotion_ready": bool(crosswalk.get("promotion_ready", False)),
        "records_scanned": scanned,
        "proprioceptive_neurons_total": proprio_total,
        "chordotonal_organ_neurons_total": chordotonal_total,
        "crosswalk_types": sorted(mapped_types),
        "crosswalk_type_count": len(mapped_types),
        "selected_feco_candidates": selected,
        "clean_selected_candidates": clean_selected,
        "review_required_selected_candidates": review_selected,
        "unresolved_proprioceptive_neurons": unresolved,
        "selected_type_counts": dict(sorted(selected_type_counts.items())),
        "selected_function_counts": dict(sorted(selected_function_counts.items())),
        "selected_mapping_status_counts": dict(
            sorted(selected_mapping_status_counts.items())
        ),
        "hook_types": sorted(hook_types),
        "hook_direction_identity": hook_identity_values,
        "directional_hook_identity_resolved": directional_hook_identity_resolved,
        "current_calibration_authorized": current_calibration_authorized,
        "expected_annotation_exceptions": expected_exceptions,
        "observed_annotation_exceptions": dict(sorted(disallowed_subclasses.items())),
        "missing_crosswalk_types": missing_types,
        "non_proprioceptive_mapped_rows": dict(sorted(non_proprio_rows.items())),
        "non_proprioceptive_name_collision_context": {
            key: dict(sorted(value.items()))
            for key, value in sorted(non_proprio_context.items())
        },
        "disallowed_subclass_rows": dict(sorted(disallowed_subclasses.items())),
        "ambiguous_related_rows_left_unresolved": dict(sorted(ambiguous_related.items())),
        "gates": gates,
        "passed": audit_passed,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "interpretation": (
            "REVIEW_REQUIRED means the pinned MaleCNS evidence exactly matches the frozen "
            "mixed-subclass SNpp41 receipt: 21 SNpp41 chordotonal-organ rows are visible to the "
            "evidence audit while one same-type subclass=leg row prevents clean exact-type "
            "promotion. SNpp39/SNpp41 extension/flexion identity also remains unresolved. "
            "No direction-specific stimulation, current calibration, receptor-current amplitude, "
            "or runtime proprioceptive stimulation is authorized."
            if is_v03
            else "PASS validates exact evidence-backed FeCO candidates only; no runtime proprioception is authorized."
        ),
    }


def _records_from_annotations(frame: Any) -> list[dict[str, Any]]:
    columns = [
        name
        for name in (
            "class",
            "cellClass",
            "cell_class",
            "subclass",
            "sub_class",
            "superclass",
            "super_class",
            "type",
            "instance",
        )
        if name in frame.columns
    ]
    return frame[columns].to_dict(orient="records")


def run_audit(
    *,
    crosswalk_path: str | Path = DEFAULT_CROSSWALK,
    output: str | Path | None = None,
) -> dict[str, Any]:
    try:
        from stonkfly.neural.common import annotations
        from stonkfly.neural.visual import VisualMemoryBrain
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "FeCO audit requires `.[stonkfly]` and prepared MaleCNS data"
        ) from exc

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
    parser = argparse.ArgumentParser(
        description="Audit evidence-backed FeCO proprioceptive types against pinned MaleCNS"
    )
    parser.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    parser.add_argument(
        "--output",
        default="runs/somatosensation/proprioception-feco-crosswalk-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_audit(crosswalk_path=args.crosswalk, output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
