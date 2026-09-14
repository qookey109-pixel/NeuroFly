from __future__ import annotations

from neurofly.proprioception_target_morphology_envelope_audit import build_report
from neurofly.proprioception_swc_asset_audit import _parse_swc


def _swc(points: list[tuple[int, int, float, float, float, float, int]]) -> bytes:
    return ("\n".join(" ".join(map(str, row)) for row in points) + "\n").encode()


def test_target_report_keeps_current_and_promotion_blocked() -> None:
    target = _swc([
        (1, 0, 0, 0, 0, 1, -1),
        (2, 5, 1, 0, 0, 1, 1),
        (3, 6, 2, 0, 0, 1, 2),
    ])
    peer_records = []
    for i in range(21):
        payload = _swc([
            (1, 0, 0, 0, 0, 1, -1),
            (2, 5, 1 + i * 0.01, 0, 0, 1, 1),
            (3, 6, 2 + i * 0.01, 0, 0, 1, 2),
        ])
        from neurofly.proprioception_swc_asset_audit import _stats
        peer_records.append({"body_id": str(1000 + i), "vfb_id": f"VFB_{i}", "swc_url": f"https://x/{i}.swc", "stats": _stats(_parse_swc(payload))})

    # The production audit is fail-closed against the exact frozen peer cohort,
    # so synthetic identity drift must not accidentally promote.
    report = build_report(target_payload=target, peer_records=peer_records)
    assert report["passed"] is False
    assert report["promotion_ready"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
