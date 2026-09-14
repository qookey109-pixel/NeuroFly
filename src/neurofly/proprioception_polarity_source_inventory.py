from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-polarity-source-inventory-v1"
DATAVERSE_PERSISTENT_ID = "doi:10.7910/DVN/7WTH1N"
DATAVERSE_API_URL = (
    "https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId="
    + urllib.parse.quote(DATAVERSE_PERSISTENT_ID, safe="")
)
KEY_TERMS = (
    "banc_888_meta.feather",
    "banc_fanc_1116_nblast.feather",
    "fanc_meta.csv",
    "fanc_meta",
    "fanc",
)


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroFly/0.4 polarity-source-inventory"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise ValueError("Dataverse API returned empty payload")
    return json.loads(payload.decode("utf-8"))


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "OK":
        raise ValueError(f"Unexpected Dataverse status: {payload.get('status')!r}")
    data = payload.get("data") or {}
    latest = data.get("latestVersion") or {}
    files = latest.get("files") or []
    records: list[dict[str, Any]] = []
    for wrapper in files:
        data_file = wrapper.get("dataFile") or {}
        label = str(data_file.get("filename") or wrapper.get("label") or "")
        directory = str(wrapper.get("directoryLabel") or "")
        logical = f"{directory}/{label}" if directory else label
        lowered = logical.lower()
        if not any(term.lower() in lowered for term in KEY_TERMS):
            continue
        records.append(
            {
                "logical_path": logical,
                "directory_label": directory,
                "filename": label,
                "file_id": data_file.get("id"),
                "filesize": data_file.get("filesize"),
                "checksum_type": (data_file.get("checksum") or {}).get("type"),
                "checksum_value": (data_file.get("checksum") or {}).get("value"),
                "content_type": data_file.get("contentType"),
                "storage_identifier": data_file.get("storageIdentifier"),
                "restricted": bool(data_file.get("restricted", False)),
            }
        )
    records.sort(key=lambda row: (row["logical_path"], str(row["file_id"])))

    exact: dict[str, list[dict[str, Any]]] = {}
    for target in ("banc_888_meta.feather", "banc_fanc_1116_nblast.feather", "fanc_meta.csv"):
        exact[target] = [row for row in records if row["filename"].lower() == target.lower()]

    canonical = {
        "schema": SCHEMA,
        "persistent_id": DATAVERSE_PERSISTENT_ID,
        "dataset_id": data.get("id"),
        "dataset_persistent_url": data.get("persistentUrl"),
        "version_number": latest.get("versionNumber"),
        "version_minor_number": latest.get("versionMinorNumber"),
        "version_state": latest.get("versionState"),
        "release_time": latest.get("releaseTime"),
        "total_files": len(files),
        "relevant_files": records,
        "exact_targets": exact,
    }
    canonical["manifest_sha256"] = _sha256_json(canonical)
    return canonical


def discover() -> dict[str, Any]:
    return parse_manifest(_fetch_json(DATAVERSE_API_URL))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = discover()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
