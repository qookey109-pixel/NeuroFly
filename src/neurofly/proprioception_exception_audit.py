from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-proprioception-snpp41-instance-exception-audit-v1"
TARGET_TYPE = "SNpp41"
TARGET_CLASS = "mechanosensory_proprioceptive"
ACCEPTED_SUBCLASS = "chordotonal organ"
EXCEPTION_SUBCLASS = "leg"
EXPECTED_TYPE_ROWS = 22
EXPECTED_ACCEPTED_ROWS = 21
EXPECTED_EXCEPTION_ROWS = 1

# Frozen from the first prepared MaleCNS discovery run 34805000350.
# Blank instance/soma_side are part of the evidence receipt. They are not
# missing values to infer or fill from morphology, laterality, or neighboring
# systematic types.
EXPECTED_EXCEPTION_IDENTITY: dict[str, str] | None = {
    "body_id": "905407",
    "instance": "",
    "type": "SNpp41",
    "class": "mechanosensory_proprioceptive",
    "subclass": "leg",
    "superclass": "vnc_sensory",
    "soma_side": "",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _identity(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        "body_id": _clean(row.get("body_id")),
        "instance": _clean(row.get("instance")),
        "type": _clean(row.get("type")),
        "class": _clean(row.get("class")).lower(),
        "subclass": _clean(row.get("subclass")).lower(),
        "superclass": _clean(row.get("superclass")).lower(),
        "soma_side": _clean(row.get("soma_side")).upper(),
    }


def _required_identity_fields_present(item: Mapping[str, str]) -> bool:
    """Require stable body/type taxonomy while permitting frozen blank metadata."""

    return all(
        item.get(key, "")
        for key in ("body_id", "type", "class", "subclass", "superclass")
    )


def audit_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in records if _clean(row.get("type")) == TARGET_TYPE]
    subclass_counts: Counter[str] = Counter(
        _clean(row.get("subclass")).lower() or "<blank>" for row in rows
    )
    class_counts: Counter[str] = Counter(
        _clean(row.get("class")).lower() or "<blank>" for row in rows
    )

    accepted = [
        row
        for row in rows
        if _clean(row.get("class")).lower() == TARGET_CLASS
        and _clean(row.get("subclass")).lower() == ACCEPTED_SUBCLASS
    ]
    exceptions = [
        row
        for row in rows
        if _clean(row.get("class")).lower() == TARGET_CLASS
        and _clean(row.get("subclass")).lower() == EXCEPTION_SUBCLASS
    ]
    unexpected = [
        row
        for row in rows
        if row not in accepted and row not in exceptions
    ]

    exception_identities = [_identity(row) for row in exceptions]
    identity_frozen = EXPECTED_EXCEPTION_IDENTITY is not None
    observed_identity = exception_identities[0] if len(exception_identities) == 1 else None
    identity_matches = (
        identity_frozen
        and observed_identity is not None
        and observed_identity == EXPECTED_EXCEPTION_IDENTITY
    )
    frozen_instance_matches = bool(
        identity_frozen
        and observed_identity is not None
        and observed_identity.get("instance")
        == EXPECTED_EXCEPTION_IDENTITY.get("instance")
    )
    frozen_soma_side_matches = bool(
        identity_frozen
        and observed_identity is not None
        and observed_identity.get("soma_side")
        == EXPECTED_EXCEPTION_IDENTITY.get("soma_side")
    )

    structural_gates = {
        "exact_type_row_count": len(rows) == EXPECTED_TYPE_ROWS,
        "exact_chordotonal_row_count": len(accepted) == EXPECTED_ACCEPTED_ROWS,
        "exact_leg_exception_count": len(exceptions) == EXPECTED_EXCEPTION_ROWS,
        "no_unexpected_snpp41_rows": len(unexpected) == 0,
        "exception_body_id_present": all(
            bool(item.get("body_id")) for item in exception_identities
        ),
        "exception_required_taxonomy_present": all(
            _required_identity_fields_present(item) for item in exception_identities
        ),
    }
    structural_pass = all(structural_gates.values())
    gates = {
        **structural_gates,
        "exception_identity_frozen": identity_frozen,
        "exception_identity_matches_frozen_receipt": bool(identity_matches),
        "instance_annotation_matches_frozen_receipt": frozen_instance_matches,
        "soma_side_annotation_matches_frozen_receipt": frozen_soma_side_matches,
        "promotion_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "current_calibration_remains_blocked": True,
    }
    passed = all(gates.values())

    if passed:
        status = "REVIEW_REQUIRED"
    elif structural_pass and not identity_frozen:
        status = "DISCOVERY_REQUIRED"
    else:
        status = "FAIL"

    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "passed": passed,
        "target_type": TARGET_TYPE,
        "expected_type_rows": EXPECTED_TYPE_ROWS,
        "type_rows": len(rows),
        "accepted_chordotonal_rows": len(accepted),
        "exception_leg_rows": len(exceptions),
        "class_counts": dict(sorted(class_counts.items())),
        "subclass_counts": dict(sorted(subclass_counts.items())),
        "exception_identities": exception_identities,
        "expected_exception_identity": EXPECTED_EXCEPTION_IDENTITY,
        "unexpected_rows": [_identity(row) for row in unexpected],
        "identity_frozen": identity_frozen,
        "blank_instance_frozen": bool(
            identity_frozen and EXPECTED_EXCEPTION_IDENTITY.get("instance") == ""
        ),
        "blank_soma_side_frozen": bool(
            identity_frozen and EXPECTED_EXCEPTION_IDENTITY.get("soma_side") == ""
        ),
        "promotion_status": "review_required",
        "promotion_ready": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "current_calibration_authorized": False,
        "gates": gates,
        "interpretation": (
            "REVIEW_REQUIRED means pinned MaleCNS reproduced the exact frozen SNpp41|leg "
            "exception identity, including bodyId 905407 and the absence of instance/somaSide "
            "annotations. Blank metadata is preserved as evidence and is never inferred. This "
            "does not promote SNpp41 for stimulation."
            if identity_frozen
            else "DISCOVERY_REQUIRED means the exact SNpp41|leg identity must be observed from "
            "pinned MaleCNS before any receipt can be frozen."
        ),
    }


def _records_from_annotations(frame: Any) -> list[dict[str, Any]]:
    """Preserve the MaleCNS bodyId index while projecting stable annotation fields."""

    records: list[dict[str, Any]] = []
    for body_id, row in frame.iterrows():
        records.append(
            {
                "body_id": str(body_id),
                "instance": row.get("instance") if "instance" in frame.columns else None,
                "type": row.get("type") if "type" in frame.columns else None,
                "class": row.get("class") if "class" in frame.columns else None,
                "subclass": row.get("subclass") if "subclass" in frame.columns else None,
                "superclass": row.get("superclass") if "superclass" in frame.columns else None,
                "soma_side": row.get("somaSide") if "somaSide" in frame.columns else None,
            }
        )
    return records


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    try:
        from stonkfly.neural.common import annotations
        from stonkfly.neural.visual import VisualMemoryBrain
    except Exception as exc:  # pragma: no cover - prepared runtime only
        raise RuntimeError(
            "SNpp41 exception audit requires `.[stonkfly]` and prepared MaleCNS data"
        ) from exc

    brain = VisualMemoryBrain()
    frame = annotations(brain.ids)
    result = audit_records(_records_from_annotations(frame))
    result["retained_neurons"] = int(len(brain.ids))
    result["stonkfly_commit"] = STONKFLY_COMMIT
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".partial")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        temporary.replace(path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the frozen MaleCNS SNpp41 mixed-subclass exception identity"
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/snpp41-instance-exception-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
