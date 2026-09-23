#!/usr/bin/env python3
"""Audit a 2026 author-published FANC↔MANC match spreadsheet for FeCO bridge IDs.

Source paper:
Guo et al. (2026), iScience 29(3):114902,
"Segmentally repeated ventral nerve cord circuits drive different leg rubbing
behaviors in Drosophila grooming", DOI 10.1016/j.isci.2026.114902.

The publisher describes Table S2 as the full dataset of matching FANC and MANC
neuron identification. This probe fetches the supplementary workbook from
publisher/PMC mirrors, parses XLSX using only Python's standard library, and
searches every cell for exact frozen NeuroFly target tokens.

A network block, missing supplement, or no token hit is never upgraded into a
positive identity claim. Only exact cells/rows are frozen for review.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import socket
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ARTICLE_DOI = "10.1016/j.isci.2026.114902"
ARTICLE_PII = "S2589004226002774"
ARTICLE_PMCID = "PMC12933626"
TABLE_LABEL = "Table S2"

SUPPLEMENT_URLS = (
    "https://ars.els-cdn.com/content/image/1-s2.0-S2589004226002774-mmc2.xlsx",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC12933626/bin/mmc2.xlsx",
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/12933626/bin/mmc2.xlsx",
)

TARGETS = {
    "manc_body_97015": "97015",
    "systematic_type_snpp41": "SNpp41",
    "banc_fanc_candidate_cell_id_20201": "20201",
    "hook_flx_root_1": "648518346481857725",
    "hook_flx_root_2": "648518346509569667",
    "hook_flx_root_3": "648518346494933426",
    "hook_flx_root_4": "648518346514448583",
    "hook_flx_root_5": "648518346494264434",
}

RECEIPT_SCHEMA = "neurofly-2026-fanc-manc-match-table-audit-v0.1"
USER_AGENT = "NeuroFly-2026-fanc-manc-match-table-audit/0.1"
TIMEOUT = 45

LOCKS = {
    "curated_r21d12_to_specific_fanc_em_identity_found": False,
    "curated_fanc_to_manc_snpp_bridge_found": False,
    "exact_polarity_verified": False,
    "current_calibration_authorized": False,
    "runtime_stimulation_authorized": False,
    "privileged_state_bypass_authorized": False,
}


def fetch_candidate(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            data = res.read()
            content_type = res.headers.get("Content-Type", "")
            final_url = res.geturl()
            valid_xlsx = (
                data.startswith(b"PK")
                and b"[Content_Types].xml" in data[:200000]
            )
            return {
                "url": url,
                "final_url": final_url,
                "http_status": int(res.status),
                "content_type": content_type,
                "byte_count": len(data),
                "valid_xlsx": valid_xlsx,
                "error": None,
                "data": data if valid_xlsx else None,
                "body_preview": "" if valid_xlsx else data[:500].decode("utf-8", errors="replace"),
            }
    except HTTPError as exc:
        data = exc.read()
        return {
            "url": url,
            "final_url": exc.geturl(),
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "byte_count": len(data),
            "valid_xlsx": False,
            "error": f"HTTPError:{exc.code}",
            "data": None,
            "body_preview": data[:500].decode("utf-8", errors="replace"),
        }
    except (URLError, TimeoutError, socket.timeout) as exc:
        return {
            "url": url,
            "final_url": url,
            "http_status": 0,
            "content_type": "",
            "byte_count": 0,
            "valid_xlsx": False,
            "error": f"{type(exc).__name__}:{exc}",
            "data": None,
            "body_preview": "",
        }


def _ns(tag: str) -> str:
    return f"{{http://schemas.openxmlformats.org/spreadsheetml/2006/main}}{tag}"


def _rels_ns(tag: str) -> str:
    return f"{{http://schemas.openxmlformats.org/package/2006/relationships}}{tag}"


def _office_rel_attr() -> str:
    return "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in zf.namelist():
        return []
    root = ET.fromstring(zf.read(path))
    out: list[str] = []
    for si in root.findall(_ns("si")):
        parts: list[str] = []
        for t in si.iter(_ns("t")):
            parts.append(t.text or "")
        out.append("".join(parts))
    return out


def load_sheet_map(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(_rels_ns("Relationship"))
    }
    sheets: list[tuple[str, str]] = []
    sheets_node = wb.find(_ns("sheets"))
    if sheets_node is None:
        return sheets
    for sheet in sheets_node.findall(_ns("sheet")):
        name = sheet.attrib.get("name", "")
        rid = sheet.attrib.get(_office_rel_attr(), "")
        target = rel_targets.get(rid, "")
        if target.startswith("/"):
            path = target.lstrip("/")
        elif target.startswith("xl/"):
            path = target
        else:
            path = "xl/" + target.lstrip("/")
        sheets.append((name, path))
    return sheets


CELL_REF_RE = re.compile(r"^([A-Z]+)([0-9]+)$")


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        is_node = cell.find(_ns("is"))
        if is_node is None:
            return ""
        return "".join((t.text or "") for t in is_node.iter(_ns("t")))
    v = cell.find(_ns("v"))
    raw = "" if v is None or v.text is None else v.text
    if cell_type == "s" and raw.isdigit():
        idx = int(raw)
        return shared[idx] if 0 <= idx < len(shared) else raw
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw


def parse_xlsx(data: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        shared = load_shared_strings(zf)
        sheet_map = load_sheet_map(zf)
        all_hits: list[dict[str, Any]] = []
        sheet_summaries: list[dict[str, Any]] = []

        for sheet_name, path in sheet_map:
            if path not in zf.namelist():
                sheet_summaries.append({
                    "sheet": sheet_name,
                    "path": path,
                    "error": "worksheet_path_missing",
                })
                continue
            root = ET.fromstring(zf.read(path))
            rows_scanned = 0
            cells_scanned = 0
            sheet_hit_count = 0
            for row in root.iter(_ns("row")):
                rows_scanned += 1
                row_cells: list[dict[str, str]] = []
                for cell in row.findall(_ns("c")):
                    ref = cell.attrib.get("r", "")
                    value = cell_value(cell, shared).strip()
                    cells_scanned += 1
                    row_cells.append({"ref": ref, "value": value})

                exact_targets = []
                for rc in row_cells:
                    for target_name, token in TARGETS.items():
                        if rc["value"] == token:
                            exact_targets.append({
                                "target": target_name,
                                "token": token,
                                "cell": rc["ref"],
                            })
                if exact_targets:
                    sheet_hit_count += len(exact_targets)
                    all_hits.append({
                        "sheet": sheet_name,
                        "row": int(row.attrib.get("r", "0") or 0),
                        "exact_targets": exact_targets,
                        "row_values": row_cells,
                    })
            sheet_summaries.append({
                "sheet": sheet_name,
                "path": path,
                "rows_scanned": rows_scanned,
                "cells_scanned": cells_scanned,
                "exact_hit_count": sheet_hit_count,
            })

    hit_tokens = {
        h["token"]
        for row in all_hits
        for h in row["exact_targets"]
    }

    rows_with_manc_and_fanc = []
    rows_with_snpp41_and_fanc = []
    fanc_tokens = {
        TARGETS["banc_fanc_candidate_cell_id_20201"],
        TARGETS["hook_flx_root_1"],
        TARGETS["hook_flx_root_2"],
        TARGETS["hook_flx_root_3"],
        TARGETS["hook_flx_root_4"],
        TARGETS["hook_flx_root_5"],
    }
    for row in all_hits:
        row_tokens = {h["token"] for h in row["exact_targets"]}
        if TARGETS["manc_body_97015"] in row_tokens and row_tokens.intersection(fanc_tokens):
            rows_with_manc_and_fanc.append(row)
        if TARGETS["systematic_type_snpp41"] in row_tokens and row_tokens.intersection(fanc_tokens):
            rows_with_snpp41_and_fanc.append(row)

    return {
        "sheet_summaries": sheet_summaries,
        "exact_hit_rows": all_hits,
        "hit_tokens": sorted(hit_tokens),
        "rows_with_manc_97015_and_fanc_target": rows_with_manc_and_fanc,
        "rows_with_snpp41_and_fanc_target": rows_with_snpp41_and_fanc,
        "direct_same_row_bridge_candidate_found": bool(
            rows_with_manc_and_fanc or rows_with_snpp41_and_fanc
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    attempts = [fetch_candidate(url) for url in SUPPLEMENT_URLS]
    chosen = next((a for a in attempts if a["valid_xlsx"]), None)

    workbook_audit = None
    parse_error = None
    if chosen is not None:
        try:
            workbook_audit = parse_xlsx(chosen["data"])
        except Exception as exc:
            parse_error = f"{type(exc).__name__}:{exc}"

    safe_attempts = []
    for a in attempts:
        safe_attempts.append({k: v for k, v in a.items() if k != "data"})

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "article_doi": ARTICLE_DOI,
            "article_pii": ARTICLE_PII,
            "article_pmcid": ARTICLE_PMCID,
            "supplement_label": TABLE_LABEL,
            "candidate_urls": list(SUPPLEMENT_URLS),
            "fetch_attempts": safe_attempts,
            "supplement_xlsx_fetched": chosen is not None,
            "chosen_url": None if chosen is None else chosen["url"],
        },
        "targets": TARGETS,
        "workbook_audit": workbook_audit,
        "summary": {
            "supplement_xlsx_fetched": chosen is not None,
            "workbook_parse_succeeded": workbook_audit is not None,
            "parse_error": parse_error,
            "direct_same_row_bridge_candidate_found": (
                False if workbook_audit is None
                else workbook_audit["direct_same_row_bridge_candidate_found"]
            ),
            "interpretation": (
                "Only exact token cells and same-row co-occurrence are frozen as "
                "candidate evidence. No morphology, fuzzy matching, or numerical "
                "same-number inference is allowed. A positive candidate still requires "
                "manual source-semantic review before any curated identity or polarity lock changes."
            ),
        },
        "locks": LOCKS,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))

    # Fetch/parse blocks are informative fail-closed outcomes, not CI failures.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
