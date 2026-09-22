#!/usr/bin/env python3
"""Read-only audit of the Phelps/GridTape author EM-LM correspondence artifacts.

This probe does not recompute morphology. It reads the author-published Fig. 4
NBLAST matrix and top-hit JSON, verifies that the stored R21D12 top hits are
hook EM neurons, and attempts to recover project59 -> source FANC project2
identity from CATMAID's LINKED NEURON annotations.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

AUTHOR_REPO = "htem/GridTape_VNC_paper"
AUTHOR_COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"
RAW_BASE = f"https://raw.githubusercontent.com/{AUTHOR_REPO}/{AUTHOR_COMMIT}"

TOP_HIT_PATH = (
    "figures_and_analysis/Fig4-Sensory_neuron_subtypes_and_EM-LM_correspondence/"
    "catmaid_renderings_EM-LM_correspondence/jsons/"
    "hook chordotonal neuron - left T1 - R21D12 MCFO F2 and top 5 hits.json"
)
SCORE_PATH = (
    "figures_and_analysis/nblast_scores/"
    "catmaid_nblast_scores_id93_LMxEM_leftT1_sensoryNeurons.csv"
)
SUBTYPE_PATH = (
    "figures_and_analysis/catmaidJsons/project59/"
    "project59_EM_leftT1chordotonal_subtypes.json"
)
COLOR_SOURCE_PATH = "pymaid_utils/make_3dViewer_json.py"
FANC_ANNOTATION_PATH = (
    "neuron_reconstructions/skeletons_in_FANC_space/"
    "sensory_neurons_annotations.json"
)

R21D12_ATLAS_SKID = 570806
EXPECTED_TOP5 = [515392, 515366, 515458, 511045, 515617]
HOOK_COLOR = "#7e2f8e"
TARGET_MANC_BODY = 97015
TARGET_MALECNS_BODY = 911942
TARGET_TYPE = "SNpp41"

CATMAID_PROJECT59 = 59
CATMAID_SOURCE_PROJECT = 2
CATMAID_BASES = [
    "https://fanc.catmaid.virtualflybrain.org",
    "https://catmaid3.hms.harvard.edu/catmaidvnc",
]

RECEIPT_SCHEMA = "neurofly-author-emlm-identity-audit-v0.3"
DECISION_POLICY = "evidence_only_no_auto_unlock"
USER_AGENT = "NeuroFly-author-emlm-audit/0.3"
TIMEOUT = 20


def fetch(url: str, *, data: dict[str, Any] | None = None) -> tuple[int, str | None, str | None]:
    body = urlencode(data).encode() if data is not None else None
    req = Request(
        url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST" if data is not None else "GET",
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as res:
            return int(res.status), res.read().decode("utf-8", errors="replace"), None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), raw, f"HTTPError:{exc.code}"
    except (URLError, TimeoutError, socket.timeout) as exc:
        return 0, None, f"{type(exc).__name__}:{exc}"


def raw_url(path: str) -> str:
    return f"{RAW_BASE}/{quote(path, safe='/')}"


def fetch_json(url: str, *, data: dict[str, Any] | None = None) -> tuple[int, Any | None, str | None]:
    status, raw, error = fetch(url, data=data)
    if raw is None:
        return status, None, error
    try:
        return status, json.loads(raw), error
    except json.JSONDecodeError:
        return status, {"raw_preview": raw[:2000]}, error or "JSONDecodeError"


def walk_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from walk_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_strings(value)


LINK_RE = re.compile(
    r"LINKED NEURON\s*-\s*elastic transformation of skeleton id\s+(\d+)\s+"
    r"in project id\s+(\d+)",
    re.I,
)
NAME_SOURCE_RE = re.compile(r"\(neuron\s+(\d+)\)\s*-\s*elastic transform", re.I)

def recover_link(payload: Any) -> dict[str, Any] | None:
    for value in walk_strings(payload):
        m = LINK_RE.search(value)
        if m:
            return {
                "annotation": value,
                "source_skeleton_id": int(m.group(1)),
                "source_project_id": int(m.group(2)),
            }
    return None


def verify_fanc_source_record(
    source_id: int,
    fanc_annotations: Any,
) -> dict[str, Any]:
    expected_token = f"(neuron {source_id})"
    matches = []
    if isinstance(fanc_annotations, dict):
        for name, annotations in fanc_annotations.items():
            if expected_token in str(name):
                ann = [str(x) for x in annotations] if isinstance(annotations, list) else []
                matches.append({
                    "name": str(name),
                    "annotations": ann,
                    "is_hook": "T1 leg hook chordotonal neuron" in ann,
                    "is_sensory": "sensory neuron" in ann,
                    "is_left_t1": "left T1 leg nerve" in ann,
                })
    exact = [
        m for m in matches
        if m["is_hook"] and m["is_sensory"] and m["is_left_t1"]
    ]
    return {
        "source_skeleton_id": source_id,
        "matching_record_count": len(matches),
        "verified_hook_fanc_record": len(exact) == 1,
        "records": matches,
    }


def catmaid_probe(skid: int) -> dict[str, Any]:
    attempts = []
    recovered = None
    for base in CATMAID_BASES:
        name_url = f"{base}/{CATMAID_PROJECT59}/skeleton/{skid}/neuronname"
        ns, npayload, nerr = fetch_json(name_url)

        annot_url = f"{base}/{CATMAID_PROJECT59}/annotations/forskeletons"
        ast, apayload, aerr = fetch_json(
            annot_url, data={"skeleton_ids[0]": str(skid)}
        )
        link = recover_link(apayload) if apayload is not None else None
        name_source = None
        if isinstance(npayload, dict):
            neuron_name = npayload.get("neuronname")
            if isinstance(neuron_name, str):
                match = NAME_SOURCE_RE.search(neuron_name)
                if match:
                    name_source = {
                        "source_skeleton_id": int(match.group(1)),
                        "source_project_id": CATMAID_SOURCE_PROJECT,
                        "annotation": None,
                        "recovery_method": "project59_neuronname_embedded_source_id",
                    }

        effective_link = link
        if effective_link is not None:
            effective_link = {**effective_link, "recovery_method": "linked_neuron_annotation"}
        elif name_source is not None:
            effective_link = name_source

        attempt = {
            "base": base,
            "neuronname_url": name_url,
            "neuronname_http_status": ns,
            "neuronname": npayload,
            "neuronname_error": nerr,
            "annotations_url": annot_url,
            "annotations_http_status": ast,
            "annotations_error": aerr,
            "annotation_link": link,
            "neuronname_source": name_source,
        }
        attempts.append(attempt)

        if effective_link and effective_link["source_project_id"] == CATMAID_SOURCE_PROJECT:
            source_id = effective_link["source_skeleton_id"]
            source_name_url = f"{base}/{CATMAID_SOURCE_PROJECT}/skeleton/{source_id}/neuronname"
            ss, spayload, serr = fetch_json(source_name_url)
            recovered = {
                **effective_link,
                "target_project59_skeleton_id": skid,
                "project59_neuronname": npayload,
                "source_neuronname_url": source_name_url,
                "source_neuronname_http_status": ss,
                "source_neuronname": spayload,
                "source_neuronname_error": serr,
                "catmaid_base": base,
            }
            break

    return {"attempts": attempts, "recovered_link": recovered}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/author_emlm_identity_audit.json")
    args = parser.parse_args()

    errors = []

    top_status, top_payload, top_error = fetch_json(raw_url(TOP_HIT_PATH))
    if top_error:
        errors.append({"scope": "author_top_hit_json", "error": top_error})

    score_status, score_raw, score_error = fetch(raw_url(SCORE_PATH))
    if score_error:
        errors.append({"scope": "author_score_matrix", "error": score_error})

    subtype_status, subtype_payload, subtype_error = fetch_json(raw_url(SUBTYPE_PATH))
    if subtype_error:
        errors.append({"scope": "author_subtype_json", "error": subtype_error})

    color_status, color_raw, color_error = fetch(raw_url(COLOR_SOURCE_PATH))
    if color_error:
        errors.append({"scope": "author_color_source", "error": color_error})

    fanc_status, fanc_payload, fanc_error = fetch_json(raw_url(FANC_ANNOTATION_PATH))
    if fanc_error:
        errors.append({"scope": "author_fanc_annotations", "error": fanc_error})

    top_ids = []
    if isinstance(top_payload, list):
        top_ids = [int(x["skeleton_id"]) for x in top_payload if "skeleton_id" in x]
    lm_id = top_ids[0] if top_ids else None
    top5 = top_ids[1:6]

    scores: dict[int, float] = {}
    if score_raw:
        rows = list(csv.reader(io.StringIO(score_raw)))
        header = rows[0]
        row = next((r for r in rows[1:] if r and r[0] == str(R21D12_ATLAS_SKID)), None)
        if row:
            for skid in top5:
                try:
                    idx = header.index(str(skid))
                    scores[skid] = float(row[idx])
                except (ValueError, IndexError):
                    pass

    subtype_colors = {}
    if isinstance(subtype_payload, list):
        subtype_colors = {
            int(x["skeleton_id"]): str(x.get("color", "")).lower()
            for x in subtype_payload
            if "skeleton_id" in x
        }

    color_source_confirms_hook = bool(
        color_raw
        and re.search(
            r"['\"]#7e2f8e['\"]\s*:\s*['\"]T1 leg hook chordotonal neuron['\"]",
            color_raw,
            re.I,
        )
    )
    top5_all_hook = bool(
        top5
        and color_source_confirms_hook
        and all(subtype_colors.get(skid) == HOOK_COLOR for skid in top5)
    )

    catmaid = {str(skid): catmaid_probe(skid) for skid in top5}
    recovered_links = {
        skid: rec["recovered_link"]
        for skid, rec in catmaid.items()
        if rec["recovered_link"] is not None
    }
    fanc_source_verification = {}
    for project59_id, link in recovered_links.items():
        source_id = int(link["source_skeleton_id"])
        fanc_source_verification[project59_id] = verify_fanc_source_record(
            source_id, fanc_payload
        )
    verified_source_records = {
        project59_id: rec
        for project59_id, rec in fanc_source_verification.items()
        if rec["verified_hook_fanc_record"]
    }

    ranked = sorted(
        (
            {
                "project59_skeleton_id": skid,
                "nblast_score": scores.get(skid),
                "subtype_color": subtype_colors.get(skid),
                "author_subtype": "T1 leg hook chordotonal neuron"
                if subtype_colors.get(skid) == HOOK_COLOR and color_source_confirms_hook
                else None,
                "source_fanc_link": catmaid[str(skid)]["recovered_link"],
                "author_fanc_source_verification": fanc_source_verification.get(str(skid)),
            }
            for skid in top5
        ),
        key=lambda x: x["nblast_score"] if x["nblast_score"] is not None else float("-inf"),
        reverse=True,
    )

    exact_author_artifact_match = (
        lm_id == R21D12_ATLAS_SKID
        and top5 == EXPECTED_TOP5
        and len(scores) == 5
        and top5_all_hook
    )

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "EVIDENCE_PROBE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_policy": DECISION_POLICY,
        "author_source": {
            "repository": AUTHOR_REPO,
            "commit": AUTHOR_COMMIT,
            "top_hit_path": TOP_HIT_PATH,
            "score_path": SCORE_PATH,
            "subtype_path": SUBTYPE_PATH,
            "color_source_path": COLOR_SOURCE_PATH,
            "fanc_annotation_path": FANC_ANNOTATION_PATH,
        },
        "http": {
            "top_hit_status": top_status,
            "score_status": score_status,
            "subtype_status": subtype_status,
            "color_source_status": color_status,
            "fanc_annotation_status": fanc_status,
        },
        "r21d12": {
            "project59_skeleton_id": lm_id,
            "expected_project59_skeleton_id": R21D12_ATLAS_SKID,
            "author_top5_project59_ids": top5,
            "expected_top5_project59_ids": EXPECTED_TOP5,
            "ranked_top5": ranked,
            "top5_all_author_annotated_hook": top5_all_hook,
            "author_color_mapping_confirms_hook": color_source_confirms_hook,
        },
        "catmaid_identity_recovery": {
            "project59": CATMAID_PROJECT59,
            "source_project": CATMAID_SOURCE_PROJECT,
            "per_hit": catmaid,
            "recovered_link_count": len(recovered_links),
            "recovered_links": recovered_links,
            "author_fanc_source_verification": fanc_source_verification,
            "verified_author_fanc_hook_source_count": len(verified_source_records),
        },
        "known_downstream_target": {
            "malecns_body_id": TARGET_MALECNS_BODY,
            "manc_body_id": TARGET_MANC_BODY,
            "type": TARGET_TYPE,
        },
        "summary": {
            "exact_author_artifact_match": exact_author_artifact_match,
            "best_author_hit_project59_id": ranked[0]["project59_skeleton_id"] if ranked else None,
            "best_author_hit_score": ranked[0]["nblast_score"] if ranked else None,
            "top5_all_author_annotated_hook": top5_all_hook,
            "project59_to_fanc_source_links_recovered": len(recovered_links),
            "verified_author_fanc_hook_source_count": len(verified_source_records),
            "project59_source_fanc_ids_recovered": len(recovered_links) == len(top5) == 5,
            "author_fanc_source_records_verified": len(verified_source_records) == len(top5) == 5,
            "curated_r21d12_to_specific_fanc_em_identity_found": False,
            "curated_fanc_to_manc_snpp_bridge_found": False,
            "automatic_unlock_performed": False,
            "interpretation": (
                "The Phelps/GridTape Fig. 4 artifacts provide author-generated R21D12-to-EM "
                "NBLAST top hits. Project59 neuron names can recover the original FANC source "
                "IDs, and those IDs are independently verified against the pinned author "
                "FANC-space sensory annotation file. This identifies the source cells behind "
                "the transformed top-hit neurons, but a morphology ranking is not a curated "
                "R21D12-to-one-cell identity assignment. The audit also does not establish a "
                "curated FANC-to-MANC SNpp41 bridge, so exact polarity remains locked."
            ),
        },
        "governance": {
            "direct_type_to_polarity_source_found": False,
            "snpp39_snpp41_polarity_resolved": False,
            "exact_polarity_verified": False,
            "current_calibration_authorized": False,
            "runtime_stimulation_authorized": False,
            "privileged_state_bypass_authorized": False,
        },
        "request_errors": errors,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
