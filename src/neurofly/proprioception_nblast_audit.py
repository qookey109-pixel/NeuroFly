from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from .upstream import STONKFLY_COMMIT


AUDIT_SCHEMA = "neurofly-proprioception-snpp41-nblast-audit-v1"
TARGET_BODY_ID = "905407"
TARGET_TYPE = "SNpp41"
TARGET_CLASS = "mechanosensory_proprioceptive"
TARGET_SUBCLASS = "leg"
PEER_SUBCLASS = "chordotonal organ"
EXPECTED_PEER_COUNT = 21

REGISTERED_BUCKET = "flyem-male-cns"
REGISTERED_PREFIX = "v1.0/segmentation/skeletons-unisex-template/"
REGISTERED_SPACE = "JRC2018U"
REGISTERED_UNITS = "um"

NAVIS_VERSION = "1.12.0"
FLYBRAINS_VERSION = "0.6.2"
NBLAST_K = 5
NBLAST_RESAMPLE_UM = 1.0
NBLAST_SCORES = "mean"
NBLAST_NORMALIZED = True
NBLAST_USE_ALPHA = False
NBLAST_SCOREMAT_REPO = "flyconnectome/nblast-scoremats"
NBLAST_SCOREMAT_COMMIT = "e2a5b027a7afe968c05ad1ac375ef3f25037f7fd"
NBLAST_SCOREMAT_PATH = "scoremats/smat_flywire_mcns.across_hemisphere.free_bins.csv"
NBLAST_SCOREMAT_URL = (
    "https://raw.githubusercontent.com/"
    f"{NBLAST_SCOREMAT_REPO}/{NBLAST_SCOREMAT_COMMIT}/{NBLAST_SCOREMAT_PATH}"
)

# Discovery-first: first prepared run publishes exact registered-skeleton source
# identities, package versions, score-matrix digest and NBLAST scores, then exits
# non-zero. A later commit may freeze only this receipt SHA256. No score cutoff is
# chosen after seeing the data.
EXPECTED_NBLAST_SHA256: str | None = None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _http_json(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroFly-evidence-audit/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Expected JSON object from public storage API")
    return payload


def _http_bytes(url: str, *, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "NeuroFly-evidence-audit/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    if not content:
        raise RuntimeError(f"Empty public evidence object: {url}")
    return content


def select_registered_object(body_id: str, items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Select exactly one registered skeleton object for ``body_id``.

    The official download page documents a public directory but not a filename
    suffix. We therefore discover the object via the Google Cloud Storage JSON
    listing API and fail closed unless exactly one object has a basename equal to
    the body id, optionally followed by one extension.
    """

    body_id = str(body_id)
    matches: list[dict[str, Any]] = []
    for item in items:
        name = _clean(item.get("name"))
        basename = name.rsplit("/", 1)[-1]
        stem = basename.split(".", 1)[0]
        if stem == body_id:
            matches.append(dict(item))
    if len(matches) != 1:
        names = sorted(_clean(item.get("name")) for item in items)
        raise RuntimeError(
            f"Expected exactly one registered skeleton for body {body_id}; "
            f"found {len(matches)} among {names}"
        )
    return matches[0]


def discover_registered_object(body_id: str) -> dict[str, Any]:
    prefix = f"{REGISTERED_PREFIX}{body_id}"
    query = urllib.parse.urlencode({"prefix": prefix})
    url = f"https://storage.googleapis.com/storage/v1/b/{REGISTERED_BUCKET}/o?{query}"
    payload = _http_json(url)
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise RuntimeError("Unexpected object listing payload")
    return select_registered_object(body_id, items)


def download_registered_object(metadata: Mapping[str, Any]) -> bytes:
    name = _clean(metadata.get("name"))
    if not name:
        raise RuntimeError("Registered skeleton metadata has no object name")
    quoted = urllib.parse.quote(name, safe="")
    url = (
        f"https://storage.googleapis.com/download/storage/v1/b/{REGISTERED_BUCKET}/o/"
        f"{quoted}?alt=media"
    )
    return _http_bytes(url)


def registered_source_receipt(metadata: Mapping[str, Any], content: bytes) -> dict[str, Any]:
    md5_base64 = _clean(metadata.get("md5Hash"))
    if md5_base64:
        expected_md5_hex = base64.b64decode(md5_base64).hex()
        actual_md5_hex = hashlib.md5(content, usedforsecurity=False).hexdigest()
        if actual_md5_hex != expected_md5_hex:
            raise RuntimeError("Registered skeleton bytes do not match GCS md5Hash")
    return {
        "object_name": _clean(metadata.get("name")),
        "generation": _clean(metadata.get("generation")),
        "size_bytes": int(metadata.get("size") or len(content)),
        "gcs_md5_base64": md5_base64,
        "gcs_crc32c_base64": _clean(metadata.get("crc32c")),
        "sha256": _sha256_bytes(content),
    }


def _annotation_record(body_id: Any, row: Mapping[str, Any]) -> dict[str, str]:
    return {
        "body_id": _clean(body_id),
        "instance": _clean(row.get("instance")),
        "type": _clean(row.get("type")),
        "class": _clean(row.get("class")).lower(),
        "subclass": _clean(row.get("subclass")).lower(),
        "superclass": _clean(row.get("superclass")).lower(),
        "soma_side": _clean(row.get("somaSide")).upper(),
    }


def describe_scores(
    *,
    target_body_id: str,
    peer_body_ids: list[str],
    pair_scores: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    target_scores = [float(pair_scores[target_body_id][peer]) for peer in peer_body_ids]
    peer_medians: list[dict[str, Any]] = []
    for body_id in peer_body_ids:
        others = [peer for peer in peer_body_ids if peer != body_id]
        values = [float(pair_scores[body_id][other]) for other in others]
        peer_medians.append(
            {
                "body_id": body_id,
                "median_best_mirror_score": round(float(median(values)), 9),
            }
        )
    target_median = float(median(target_scores))
    baseline = [row["median_best_mirror_score"] for row in peer_medians]
    percentile = 100.0 * sum(value <= target_median for value in baseline) / len(baseline)
    return {
        "target_vs_peers": [
            {
                "body_id": peer,
                "best_mirror_score": round(float(pair_scores[target_body_id][peer]), 9),
            }
            for peer in sorted(peer_body_ids)
        ],
        "target_median_best_mirror_score": round(target_median, 9),
        "peer_leave_one_out_medians": sorted(peer_medians, key=lambda row: row["body_id"]),
        "peer_baseline": {
            "minimum_median_best_mirror_score": round(float(min(baseline)), 9),
            "median_median_best_mirror_score": round(float(median(baseline)), 9),
            "maximum_median_best_mirror_score": round(float(max(baseline)), 9),
            "target_percentile_among_peer_medians": round(percentile, 9),
        },
    }


def _canonical_receipt(
    *,
    target_body_id: str,
    peer_body_ids: list[str],
    sources: Mapping[str, Mapping[str, Any]],
    scoremat_sha256: str,
    package_versions: Mapping[str, str],
    score_variants: Mapping[str, Mapping[str, Mapping[str, float]]],
    pair_scores: Mapping[str, Mapping[str, float]],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "registered_source": {
            "release": "MaleCNS v1.0",
            "template": REGISTERED_SPACE,
            "units": REGISTERED_UNITS,
            "bucket": REGISTERED_BUCKET,
            "prefix": REGISTERED_PREFIX,
            "skeletons": {body_id: sources[body_id] for body_id in sorted(sources)},
        },
        "nblast": {
            "navis_version": package_versions["navis"],
            "flybrains_version": package_versions["flybrains"],
            "dotprops_k": NBLAST_K,
            "resample_um": NBLAST_RESAMPLE_UM,
            "scores": NBLAST_SCORES,
            "normalized": NBLAST_NORMALIZED,
            "use_alpha": NBLAST_USE_ALPHA,
            "mirror_template": REGISTERED_SPACE,
            "mirror_policy": "maximum-of-original/mirrored-pair-variants",
            "scoremat_repo": NBLAST_SCOREMAT_REPO,
            "scoremat_commit": NBLAST_SCOREMAT_COMMIT,
            "scoremat_path": NBLAST_SCOREMAT_PATH,
            "scoremat_sha256": scoremat_sha256,
        },
        "target_body_id": target_body_id,
        "peer_body_ids": sorted(peer_body_ids),
        "score_variants": score_variants,
        "best_mirror_pair_scores": pair_scores,
        "comparison": comparison,
    }


def audit_nblast(
    *,
    target_record: Mapping[str, Any],
    peer_records: Iterable[Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
    scoremat_sha256: str,
    package_versions: Mapping[str, str],
    score_variants: Mapping[str, Mapping[str, Mapping[str, float]]],
    pair_scores: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    target_body_id = _clean(target_record.get("body_id"))
    peers = [dict(row) for row in peer_records]
    peer_body_ids = sorted(_clean(row.get("body_id")) for row in peers)
    expected_ids = {target_body_id, *peer_body_ids}
    comparison = describe_scores(
        target_body_id=target_body_id,
        peer_body_ids=peer_body_ids,
        pair_scores=pair_scores,
    )
    canonical = _canonical_receipt(
        target_body_id=target_body_id,
        peer_body_ids=peer_body_ids,
        sources=sources,
        scoremat_sha256=scoremat_sha256,
        package_versions=package_versions,
        score_variants=score_variants,
        pair_scores=pair_scores,
        comparison=comparison,
    )
    digest = _sha256_json(canonical)
    frozen = EXPECTED_NBLAST_SHA256 is not None

    all_scores_finite = all(
        math.isfinite(float(score))
        for row in pair_scores.values()
        for score in row.values()
    )
    structural_gates = {
        "target_body_matches_frozen_identity": target_body_id == TARGET_BODY_ID,
        "target_type_is_snpp41": _clean(target_record.get("type")) == TARGET_TYPE,
        "target_class_matches": _clean(target_record.get("class")).lower() == TARGET_CLASS,
        "target_subclass_is_leg": _clean(target_record.get("subclass")).lower() == TARGET_SUBCLASS,
        "exact_peer_count": len(peers) == EXPECTED_PEER_COUNT,
        "all_peers_are_snpp41": all(_clean(row.get("type")) == TARGET_TYPE for row in peers),
        "all_peers_match_class": all(
            _clean(row.get("class")).lower() == TARGET_CLASS for row in peers
        ),
        "all_peers_are_chordotonal": all(
            _clean(row.get("subclass")).lower() == PEER_SUBCLASS for row in peers
        ),
        "all_registered_skeletons_present": set(sources) == expected_ids,
        "all_registered_skeleton_sha_present": all(
            len(_clean(row.get("sha256"))) == 64 for row in sources.values()
        ),
        "exact_navis_version": package_versions.get("navis") == NAVIS_VERSION,
        "exact_flybrains_version": package_versions.get("flybrains") == FLYBRAINS_VERSION,
        "scoremat_sha_present": len(scoremat_sha256) == 64,
        "all_pair_scores_present": set(pair_scores) == expected_ids
        and all(set(row) == expected_ids for row in pair_scores.values()),
        "all_pair_scores_finite": all_scores_finite,
    }
    structural_pass = all(structural_gates.values())
    digest_matches = frozen and digest == EXPECTED_NBLAST_SHA256
    gates = {
        **structural_gates,
        "nblast_receipt_frozen": frozen,
        "nblast_receipt_matches": bool(digest_matches),
        "promotion_remains_blocked": True,
        "stimulation_remains_disabled": True,
        "runtime_transduction_remains_disabled": True,
        "current_calibration_remains_blocked": True,
        "direction_tuning_remains_unresolved": True,
    }
    passed = all(gates.values())
    if passed:
        status = "REVIEW_REQUIRED"
    elif structural_pass and not frozen:
        status = "DISCOVERY_REQUIRED"
    else:
        status = "FAIL"

    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "passed": passed,
        "target": {
            "body_id": target_body_id,
            "type": _clean(target_record.get("type")),
            "class": _clean(target_record.get("class")).lower(),
            "subclass": _clean(target_record.get("subclass")).lower(),
            "superclass": _clean(target_record.get("superclass")).lower(),
            "instance": _clean(target_record.get("instance")),
            "soma_side": _clean(target_record.get("soma_side")).upper(),
        },
        "peer_count": len(peers),
        "peer_body_ids": peer_body_ids,
        "registered_skeleton_sources": {
            body_id: sources[body_id] for body_id in sorted(sources)
        },
        "nblast": canonical["nblast"],
        "comparison": comparison,
        "nblast_sha256": digest,
        "expected_nblast_sha256": EXPECTED_NBLAST_SHA256,
        "receipt_frozen": frozen,
        "registered_morphology_evidence_present": structural_gates["all_registered_skeletons_present"],
        "promotion_ready": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "current_calibration_authorized": False,
        "direction_tuning_resolved": False,
        "gates": gates,
        "interpretation": (
            "Registered-space NBLAST is a morphology-similarity evidence layer only. "
            "DISCOVERY_REQUIRED intentionally uses no post-hoc score cutoff and does not "
            "classify body 905407 as hook/non-hook or resolve SNpp39/SNpp41 extension/flexion "
            "tuning. Current calibration, stimulation and promotion remain blocked."
        ),
    }


def _load_tree_neuron(navis: Any, content: bytes, body_id: str, directory: Path) -> Any:
    path = directory / f"{body_id}.swc"
    path.write_bytes(content)
    neuron = navis.read_swc(path)
    if hasattr(neuron, "__len__") and not hasattr(neuron, "nodes"):
        if len(neuron) != 1:
            raise RuntimeError(f"Expected one neuron in registered skeleton {body_id}")
        neuron = neuron[0]
    neuron.id = body_id
    neuron.name = body_id
    try:
        neuron.units = "1 um"
    except Exception:
        pass
    return neuron


def _matrix_to_nested(matrix: Any, ids: list[str]) -> dict[str, dict[str, float]]:
    return {
        query: {target: round(float(matrix.loc[query, target]), 9) for target in ids}
        for query in ids
    }


def _best_pair_scores(
    ids: list[str],
    variants: Mapping[str, Mapping[str, Mapping[str, float]]],
) -> dict[str, dict[str, float]]:
    names = ("oo", "om", "mo", "mm")
    return {
        query: {
            target: round(max(float(variants[name][query][target]) for name in names), 9)
            for target in ids
        }
        for query in ids
    }


def run_audit(*, output: str | Path | None = None) -> dict[str, Any]:
    try:
        import numpy as np
        import pandas as pd
        import pyarrow.feather as feather
        import navis
        import flybrains  # noqa: F401 - registers JRC2018U template with navis
        from importlib.metadata import version
        from stonkfly.neural.common import DATA
    except Exception as exc:  # pragma: no cover - prepared workflow only
        raise RuntimeError(
            "SNpp41 NBLAST audit requires prepared MaleCNS plus pinned navis/flybrains"
        ) from exc

    package_versions = {
        "navis": version("navis"),
        "flybrains": version("flybrains"),
    }
    if package_versions["navis"] != NAVIS_VERSION:
        raise RuntimeError(f"Unexpected navis version: {package_versions['navis']}")
    if package_versions["flybrains"] != FLYBRAINS_VERSION:
        raise RuntimeError(f"Unexpected flybrains version: {package_versions['flybrains']}")

    nodes = feather.read_table(DATA / "normalized/neurons.feather").to_pandas()
    retained_ids = nodes.source_id.to_numpy(dtype=np.int64)
    annotations = (
        feather.read_table(DATA / "annotations.feather")
        .to_pandas()
        .set_index("bodyId")
        .loc[retained_ids]
    )

    target_matches = np.flatnonzero(retained_ids == int(TARGET_BODY_ID))
    if len(target_matches) != 1:
        raise RuntimeError(f"Expected exactly one retained body {TARGET_BODY_ID}")
    target_index = int(target_matches[0])
    target_record = _annotation_record(retained_ids[target_index], annotations.iloc[target_index])

    peer_mask = (
        annotations.type.fillna("").astype(str).eq(TARGET_TYPE)
        & annotations["class"].fillna("").astype(str).str.lower().eq(TARGET_CLASS)
        & annotations.subclass.fillna("").astype(str).str.lower().eq(PEER_SUBCLASS)
    ).to_numpy()
    peer_indices = np.flatnonzero(peer_mask)
    peer_records = [_annotation_record(retained_ids[i], annotations.iloc[i]) for i in peer_indices]
    peer_body_ids = sorted(row["body_id"] for row in peer_records)
    ids = [TARGET_BODY_ID, *peer_body_ids]

    scoremat_bytes = _http_bytes(NBLAST_SCOREMAT_URL)
    scoremat_sha256 = _sha256_bytes(scoremat_bytes)

    sources: dict[str, dict[str, Any]] = {}
    contents: dict[str, bytes] = {}
    for body_id in ids:
        metadata = discover_registered_object(body_id)
        content = download_registered_object(metadata)
        sources[body_id] = registered_source_receipt(metadata, content)
        contents[body_id] = content

    with tempfile.TemporaryDirectory(prefix="neurofly-nblast-") as tmp:
        directory = Path(tmp)
        neurons = [
            _load_tree_neuron(navis, contents[body_id], body_id, directory)
            for body_id in ids
        ]
        neuron_list = navis.NeuronList(neurons)
        dotprops = navis.make_dotprops(
            neuron_list,
            k=NBLAST_K,
            resample=NBLAST_RESAMPLE_UM,
            parallel=False,
        )
        for body_id, dp in zip(ids, dotprops):
            dp.id = body_id
            dp.name = body_id
        mirrored = navis.mirror_brain(dotprops, template=REGISTERED_SPACE)
        for body_id, dp in zip(ids, mirrored):
            dp.id = body_id
            dp.name = body_id

        scoremat_path = directory / "scoremat.csv"
        scoremat_path.write_bytes(scoremat_bytes)
        smat = pd.read_csv(scoremat_path, index_col=0)

        kwargs = dict(
            use_alpha=NBLAST_USE_ALPHA,
            scores=NBLAST_SCORES,
            normalized=NBLAST_NORMALIZED,
            smat=smat,
            n_cores=1,
            progress=False,
        )
        oo = navis.nblast(dotprops, dotprops, **kwargs)
        om = navis.nblast(dotprops, mirrored, **kwargs)
        mo = navis.nblast(mirrored, dotprops, **kwargs)
        mm = navis.nblast(mirrored, mirrored, **kwargs)
        for matrix in (oo, om, mo, mm):
            matrix.index = ids
            matrix.columns = ids

    score_variants = {
        "oo": _matrix_to_nested(oo, ids),
        "om": _matrix_to_nested(om, ids),
        "mo": _matrix_to_nested(mo, ids),
        "mm": _matrix_to_nested(mm, ids),
    }
    pair_scores = _best_pair_scores(ids, score_variants)
    result = audit_nblast(
        target_record=target_record,
        peer_records=peer_records,
        sources=sources,
        scoremat_sha256=scoremat_sha256,
        package_versions=package_versions,
        score_variants=score_variants,
        pair_scores=pair_scores,
    )
    result["retained_neurons"] = int(len(retained_ids))
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
        description="Discover/freeze registered-space NBLAST evidence for SNpp41 body 905407"
    )
    parser.add_argument(
        "--output",
        default="runs/somatosensation/snpp41-body905407-nblast-audit.json",
    )
    args = parser.parse_args(argv)
    result = run_audit(output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
