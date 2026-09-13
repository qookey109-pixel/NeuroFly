from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-gustation-functional-crosswalk-audit-v1"
DEFAULT_CROSSWALK = Path("data/gustation_functional_crosswalk_v01.json")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def load_crosswalk(path: str | Path = DEFAULT_CROSSWALK) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema") != "neurofly-gustation-functional-crosswalk-v0.1":
        raise ValueError("Unsupported gustation crosswalk schema")
    if payload.get("stimulation_enabled") is not False:
        raise ValueError("Crosswalk discovery must not enable stimulation")
    mappings = payload.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("Gustation crosswalk must contain mappings")

    seen: set[str] = set()
    for mapping in mappings:
        neuron_type = _clean(mapping.get("male_cns_type"))
        functional_class = _clean(mapping.get("functional_class"))
        if not neuron_type or not functional_class:
            raise ValueError("Each crosswalk mapping needs male_cns_type and functional_class")
        if neuron_type in seen:
            raise ValueError(f"Duplicate MaleCNS type in crosswalk: {neuron_type}")
        seen.add(neuron_type)
        if mapping.get("stimulation_authorized") is not False:
            raise ValueError("Functional crosswalk must not authorize stimulation")
        evidence = mapping.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Missing evidence for {neuron_type}")
        for item in evidence:
            if not _clean(item.get("kind")) or not _clean(item.get("url")):
                raise ValueError(f"Incomplete evidence for {neuron_type}")
    return payload


def audit_records(
    records: Iterable[Mapping[str, Any]],
    crosswalk: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify only explicitly mapped functional classes against curated MaleCNS rows."""

    mappings = {
        _clean(item["male_cns_type"]): item
        for item in crosswalk["mappings"]
    }
    mapped_types = set(mappings)
    scanned = 0
    gustatory_total = 0
    mapped_neurons = 0
    mapped_type_counts: Counter[str] = Counter()
    functional_counts: Counter[str] = Counter()
    non_gustatory_mapped_rows: Counter[str] = Counter()
    all_gustatory_type_counts: Counter[str] = Counter()

    for row in records:
        scanned += 1
        neuron_class = _clean(
            row.get("class", row.get("cellClass", row.get("cell_class")))
        ).lower()
        neuron_type = _clean(row.get("type"))
        if neuron_class == "gustatory":
            gustatory_total += 1
            if neuron_type:
                all_gustatory_type_counts[neuron_type] += 1

        if neuron_type not in mapped_types:
            continue
        if neuron_class != "gustatory":
            non_gustatory_mapped_rows[neuron_type] += 1
            continue

        mapped_neurons += 1
        mapped_type_counts[neuron_type] += 1
        functional_counts[_clean(mappings[neuron_type]["functional_class"])] += 1

    missing_types = sorted(mapped_types - set(mapped_type_counts))
    unexpected_non_gustatory = dict(sorted(non_gustatory_mapped_rows.items()))
    unresolved_gustatory = gustatory_total - mapped_neurons

    gates = {
        "all_crosswalk_types_present": not missing_types,
        "all_mapped_rows_are_curated_gustatory": not unexpected_non_gustatory,
        "mapped_population_nonempty": mapped_neurons > 0,
        "unresolved_population_preserved": unresolved_gustatory >= 0,
        "stimulation_remains_disabled": crosswalk.get("stimulation_enabled") is False,
    }
    passed = all(gates.values())

    return {
        "schema": AUDIT_SCHEMA,
        "crosswalk_schema": crosswalk["schema"],
        "policy": crosswalk.get("policy"),
        "records_scanned": scanned,
        "gustatory_neurons_total": gustatory_total,
        "mapped_neurons": mapped_neurons,
        "unresolved_gustatory_neurons": unresolved_gustatory,
        "mapped_fraction": (
            round(mapped_neurons / gustatory_total, 8) if gustatory_total else 0.0
        ),
        "mapped_type_counts": dict(sorted(mapped_type_counts.items())),
        "functional_class_counts": dict(sorted(functional_counts.items())),
        "missing_crosswalk_types": missing_types,
        "non_gustatory_mapped_rows": unexpected_non_gustatory,
        "gates": gates,
        "passed": passed,
        "stimulation_enabled": False,
        "interpretation": (
            "PASS validates only that the conservative evidence-backed type mapping "
            "exists in the exact pinned MaleCNS gustatory population. Unmapped GRNs "
            "remain unresolved and no gustatory current is authorized."
        ),
    }


def _records_from_annotations(frame: Any) -> list[dict[str, Any]]:
    columns = [
        name
        for name in ("class", "cellClass", "cell_class", "type", "instance")
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
            "MaleCNS gustation crosswalk audit requires `.[stonkfly]` and prepared data."
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
        description="Audit evidence-backed gustatory functional types against pinned MaleCNS"
    )
    parser.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    parser.add_argument(
        "--output",
        default="runs/gustation/gustation-functional-crosswalk-audit.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_audit(crosswalk_path=args.crosswalk, output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
