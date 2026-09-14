from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-polarity-reviewed-match-discovery-v1"
DATAVERSE_FILE_ID = 13994486
DATAVERSE_FILE_MD5 = "350812b78ddf41598189473877158cee"
DATAVERSE_ACCESS_URL = f"https://dataverse.harvard.edu/api/access/datafile/{DATAVERSE_FILE_ID}"
KEYWORDS = ("snpp39", "snpp41", "hook_flx", "hook_ext", "hook flex", "hook ext")


def _download() -> bytes:
    request = urllib.request.Request(DATAVERSE_ACCESS_URL, headers={"User-Agent": "NeuroFly/0.4 reviewed-match-discovery"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise ValueError("Reviewed-match archive is empty")
    return payload


def inspect(payload: bytes) -> dict[str, Any]:
    import hashlib

    md5 = hashlib.md5(payload).hexdigest()
    text = gzip.decompress(payload).decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Reviewed-match CSV has no header")
    rows = list(reader)
    hits: list[dict[str, str]] = []
    for row in rows:
        haystack = " | ".join(str(value or "") for value in row.values()).lower()
        if any(keyword in haystack for keyword in KEYWORDS):
            hits.append({key: str(value or "") for key, value in row.items()})
    return {
        "schema": SCHEMA,
        "dataverse_file_id": DATAVERSE_FILE_ID,
        "expected_md5": DATAVERSE_FILE_MD5,
        "observed_md5": md5,
        "md5_matches": md5 == DATAVERSE_FILE_MD5,
        "compressed_bytes": len(payload),
        "csv_columns": list(reader.fieldnames),
        "row_count": len(rows),
        "keyword_hit_count": len(hits),
        "keyword_hits": hits,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = inspect(_download())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["md5_matches"] else 1


if __name__ == "__main__":
    sys.exit(main())
