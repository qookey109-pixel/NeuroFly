from __future__ import annotations

import json
from pathlib import Path

CANDIDATES = (
    "DNp09",
    "BDN2",
    "oDN1",
    "DNg97",
    "DNg100",
    "DNb02",
    "DNa01",
    "DNa02",
)


def main() -> None:
    from stonkfly.neural.common import annotations
    from stonkfly.neural.visual import VisualMemoryBrain

    brain = VisualMemoryBrain()
    table = annotations(brain.ids)
    types = table.type.fillna("").astype(str)
    sides = table.somaSide.fillna("").astype(str).str.upper()
    instances = (
        table["instance"].fillna("").astype(str)
        if "instance" in table.columns
        else types.map(lambda _: "")
    )

    rows = {}
    for neuron_type in CANDIDATES:
        mask = types.eq(neuron_type)
        indices = [int(i) for i in __import__("numpy").flatnonzero(mask.to_numpy()).tolist()]
        cells = []
        for i in indices:
            cells.append(
                {
                    "index": i,
                    "body_id": str(brain.ids[i]),
                    "soma_side": str(sides.iloc[i]),
                    "instance": str(instances.iloc[i]),
                }
            )
        rows[neuron_type] = {"count": len(cells), "cells": cells}

    payload = {
        "schema": "neurofly-walking-dn-population-audit-v1",
        "backend": "stonkfly.VisualMemoryBrain",
        "candidate_types": list(CANDIDATES),
        "types": rows,
    }
    out = Path("artifacts/walking_dn_population_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
