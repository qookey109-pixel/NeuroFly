#!/usr/bin/env python3
"""Recover stable FANC cell IDs for the frozen T1L hook_flx root set.

Requires an already-authorized CAVE client session. No token or credential is
read from command-line arguments, written to output, or stored in the repo.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DEFAULT_ROOTS = Path("data/research/feco/fanc_v840_t1l_hook_flx_roots.csv")
DEFAULT_OUTPUT = Path("data/research/feco/fanc_v840_t1l_hook_flx_stable_ids.csv")
DEFAULT_DATASTACK = "fanc_production_mar2021"
DEFAULT_MATERIALIZATION = 840


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", type=Path, default=DEFAULT_ROOTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--datastack", default=DEFAULT_DATASTACK)
    parser.add_argument("--materialization", type=int, default=DEFAULT_MATERIALIZATION)
    return parser.parse_args()


def load_roots(path: Path) -> list[int]:
    df = pd.read_csv(path, dtype={"pt_root_id": "string"})
    if "pt_root_id" not in df.columns:
        raise ValueError(f"{path} is missing pt_root_id")
    roots = [int(value) for value in df["pt_root_id"].dropna().tolist()]
    if len(roots) != len(set(roots)):
        raise ValueError("duplicate pt_root_id values in frozen root set")
    if len(roots) != 13:
        raise ValueError(f"expected 13 frozen hook_flx roots, got {len(roots)}")
    return roots


def query_cell_ids(datastack: str, materialization: int, roots: list[int]) -> pd.DataFrame:
    try:
        from caveclient import CAVEclient
    except ImportError as exc:
        raise SystemExit(
            "caveclient is required for this authenticated research step; "
            "install it in an isolated research environment."
        ) from exc

    client = CAVEclient(datastack)
    client.materialize.version = materialization
    result = client.materialize.query_table(
        "cell_ids_v2",
        filter_in_dict={"pt_root_id": roots},
    )
    return result


def build_output(roots: list[int], result: pd.DataFrame) -> pd.DataFrame:
    required = {"pt_root_id"}
    missing = required - set(result.columns)
    if missing:
        raise ValueError(f"cell_ids_v2 result missing required columns: {sorted(missing)}")

    keep = [
        column
        for column in (
            "id",
            "user_id",
            "pt_root_id",
            "pt_supervoxel_id",
            "pt_position",
            "valid",
        )
        if column in result.columns
    ]
    result = result[keep].copy()
    result["pt_root_id"] = result["pt_root_id"].astype("string")

    counts = result.groupby("pt_root_id").size()
    duplicates = counts[counts > 1]
    if not duplicates.empty:
        raise ValueError(
            "cell_ids_v2 returned multiple rows for frozen roots: "
            + ", ".join(duplicates.index.tolist())
        )

    base = pd.DataFrame({"pt_root_id": [str(root) for root in roots]})
    out = base.merge(result, on="pt_root_id", how="left", validate="one_to_one")

    if "id" in out.columns and "user_id" in out.columns:
        out["id_equals_user_id"] = (
            out["id"].notna()
            & out["user_id"].notna()
            & (out["id"].astype("string") == out["user_id"].astype("string"))
        )
    else:
        out["id_equals_user_id"] = False

    out["mapping_recovered"] = out[[c for c in ("id", "user_id") if c in out.columns]].notna().any(axis=1)
    return out


def main() -> int:
    args = parse_args()
    roots = load_roots(args.roots)
    result = query_cell_ids(args.datastack, args.materialization, roots)
    output = build_output(roots, result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)

    recovered = int(output["mapping_recovered"].sum())
    equal = int(output["id_equals_user_id"].sum())
    print(f"recovered={recovered}/13 id_equals_user_id={equal}/13")
    print(args.output)

    # Evidence is not promotion. Refuse a silent partial-success interpretation.
    return 0 if recovered == 13 else 2


if __name__ == "__main__":
    raise SystemExit(main())
