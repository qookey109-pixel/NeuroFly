from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-tactile-leg-functional-crosswalk-audit-v1"
DEFAULT_CROSSWALK = Path("data/tactile_leg_functional_crosswalk_v01.json")
TARGET_CLASS = "mechanosensory_tactile"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def load_crosswalk(path: str | Path = DEFAULT_CROSSWALK) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema") != "neurofly-tactile-leg-functional-crosswalk-v0.1":
        raise ValueError("Unsupported tactile leg crosswalk schema")
    if payload.get("source_population_class") != TARGET_CLASS:
        raise ValueError("Tactile leg crosswalk must target mechanosensory_tactile")
    if payload.get("stimulation_enabled") is not False:
        raise ValueError("Tactile crosswalk discovery must not enable stimulation")
    if payload.get("runtime_transduction_enabled") is not False:
        raise ValueError("Tactile crosswalk discovery must not enable runtime transduction")

    accepted = payload.get("accepted_curator_subclasses")
    if not isinstance(accepted, list) or not accepted:
        raise ValueError("Tactile crosswalk needs accepted_curator_subclasses")
    accepted_clean = {_clean(item).lower() for item in accepted}
    if accepted_clean != {"leg", "mechanosensory bristle"}:
        raise ValueError("Unexpected tactile accepted subclass policy")

    mappings = payload.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("Tactile leg crosswalk must contain mappings")

    seen: set[str] = set()
    for mapping in mappings:
        neuron_type = _clean(mapping.get("male_cns_type"))
        functional_class = _clean(mapping.get("functional_class"))
        if not neuron_type or not functional_class:
            raise ValueError("Each mapping needs male_cns_type and functional_class")
        if "," in neuron_type:
            raise ValueError("Crosswalk mappings must use exact single MaleCNS types")
        if neuron_type in seen:
            raise ValueError(f"Duplicate tactile MaleCNS type: {neuron_type}")
        seen.add(neuron_type)
        if mapping.get("stimulation_authorized") is not False:
            raise ValueError("Tactile crosswalk must not authorize stimulation")
        evidence = mapping.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Missing anatomical evidence for {neuron_type}")
        for item in evidence:
            if not _clean(item.get("kind")) or not _clean(item.get("url")) or not _clean(item.get("claim")):
                raise ValueError(f"Incomplete anatomical evidence for {neuron_type}")
    return payload


def audit_records(
    records: Iterable[Mapping[str, Any]],
    crosswalk: Mapping[str, Any],
) -> dict[str, Any]:
    """Intersect exact retained tactile types with explicit leg-nerve evidence.

    The crosswalk is intentionally type-exact. Combined curator labels such as
    ``SNta27,SNta28`` remain unresolved rather than being split or promoted.
    ``leg`` and ``mechanosensory bristle`` are the only accepted subclasses;
    mapped types appearing as notum/wing/etc. make the audit fail so a type-level
    anatomical assumption cannot silently spread into another body region.
    """

    mappings = {
        _clean(item["male_cns_type"]): item
        for item in crosswalk["mappings"]
    }
    mapped_types = set(mappings)
    accepted_subclasses = {
        _clean(value).lower()
        for value in crosswalk["accepted_curator_subclasses"]
    }

    scanned = 0
    tactile_total = 0
    selected_neurons = 0
    selected_type_counts: Counter[str] = Counter()
    selected_subclass_counts: Counter[str] = Counter()
    evidence_tier_counts: Counter[str] = Counter()
    non_tactile_mapped_rows: Counter[str] = Counter()
    disallowed_subclass_rows: Counter[str] = Counter()
    ambiguous_related_rows: Counter[str] = Counter()
    all_tactile_type_counts: Counter[str] = Counter()

    for row in records:
        scanned += 1
        neuron_class = _clean(
            row.get("class", row.get("cellClass", row.get("cell_class")))
        ).lower()
        neuron_type = _clean(row.get("type"))
        subclass = _clean(row.get("subclass", row.get("sub_class"))).lower()

        if neuron_class == TARGET_CLASS:
            tactile_total += 1
            if neuron_type:
                all_tactile_type_counts[neuron_type] += 1

        # Combined labels are never split. Count only mixtures that mention at
        # least one approved exact type so the unresolved boundary is visible.
        if neuron_class == TARGET_CLASS and "," in neuron_type:
            parts = {_clean(part) for part in neuron_type.split(",") if _clean(part)}
            if parts & mapped_types:
                ambiguous_related_rows[neuron_type] += 1

        if neuron_type not in mapped_types:
            continue
        if neuron_class != TARGET_CLASS:
            non_tactile_mapped_rows[neuron_type] += 1
            continue
        if subclass not in accepted_subclasses:
            key = f"{neuron_type}|{subclass or '<blank>'}"
            disallowed_subclass_rows[key] += 1
            continue

        selected_neurons += 1
        selected_type_counts[neuron_type] += 1
        selected_subclass_counts[subclass] += 1
        if subclass == "leg":
            evidence_tier_counts["curator_leg_plus_external_nerve"] += 1
        else:
            evidence_tier_counts["external_leg_nerve_plus_bristle_class"] += 1

    missing_types = sorted(mapped_types - set(selected_type_counts))
    unresolved_tactile = tactile_total - selected_neurons
    gates = {
        "all_crosswalk_types_present": not missing_types,
        "all_selected_rows_are_curated_tactile": not non_tactile_mapped_rows,
        "no_mapped_type_leaks_into_disallowed_subclasses": not disallowed_subclass_rows,
        "selected_population_nonempty": selected_neurons > 0,
        "ambiguous_combined_labels_remain_unselected": True,
        "unresolved_population_preserved": unresolved_tactile >= 0,
        "stimulation_remains_disabled": crosswalk.get("stimulation_enabled") is False,
        "runtime_transduction_remains_disabled": crosswalk.get("runtime_transduction_enabled") is False,
    }
    passed = all(gates.values())

    return {
        "schema": AUDIT_SCHEMA,
        "crosswalk_schema": crosswalk["schema"],
        "policy": crosswalk.get("policy"),
        "records_scanned": scanned,
        "tactile_neurons_total": tactile_total,
        "crosswalk_types": sorted(mapped_types),
        "crosswalk_type_count": len(mapped_types),
        "selected_leg_touch_candidates": selected_neurons,
        "unresolved_tactile_neurons": unresolved_tactile,
        "selected_fraction": (
            round(selected_neurons / tactile_total, 8) if tactile_total else 0.0
        ),
        "selected_type_counts": dict(sorted(selected_type_counts.items())),
        "selected_subclass_counts": dict(sorted(selected_subclass_counts.items())),
        "evidence_tier_counts": dict(sorted(evidence_tier_counts.items())),
        "missing_crosswalk_types": missing_types,
        "non_tactile_mapped_rows": dict(sorted(non_tactile_mapped_rows.items())),
        "disallowed_subclass_rows": dict(sorted(disallowed_subclass_rows.items())),
        "ambiguous_related_rows_left_unresolved": dict(sorted(ambiguous_related_rows.items())),
        "gates": gates,
        "passed": passed,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "interpretation": (
            "PASS validates only a conservative evidence-backed leg-associated tactile "
            "candidate population in the exact pinned MaleCNS annotations. Combined "
            "labels and all unsupported tactile neurons remain unresolved. No tactile "
            "current or runtime contact signal is authorized."
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
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(
            "MaleCNS tactile leg crosswalk audit requires `.[stonkfly]` and prepared data."
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit evidence-backed leg tactile types against pinned MaleCNS"
    )
    parser.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    parser.add_argument(
        "--output",
        default="runs/somatosensation/tactile-leg-functional-crosswalk-audit.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_audit(crosswalk_path=args.crosswalk, output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
