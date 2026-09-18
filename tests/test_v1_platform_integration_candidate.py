from __future__ import annotations

import json
from pathlib import Path

from neurofly.environment_adapter import make_environment_adapter
from neurofly.thermosensation import thermal_change_sensation


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "v1_platform_integration_candidate_v01.json"


def test_v1_integration_manifest_is_exact_and_non_promotional() -> None:
    manifest = json.loads(MANIFEST.read_text())

    assert manifest["schema"] == "neurofly-v1-platform-integration-candidate-v0.1"
    assert manifest["status"] == "REVIEW_REQUIRED"
    assert manifest["source_prs"] == {
        "thermosensation": 86,
        "light_chase": 87,
        "learning_controls": 88,
        "forced_crash_recovery": 89,
        "environment_adapter": 90,
        "platform_dashboard": 91,
        "real_light_chase_smoke": 92,
    }
    assert all(manifest["included_capabilities"].values())
    assert all(manifest["preserved_legacy_paths"].values())
    assert all(manifest["not_included"].values())
    assert all(value is False for value in manifest["claims_locked_false"].values())
    assert manifest["merge_policy"] == {
        "merge_main_authorized": False,
        "real_execution_receipts_required_after_authority_integration": True,
    }


def test_v1_candidate_contains_required_product_surfaces() -> None:
    required = [
        "src/neurofly/thermosensation.py",
        "src/neurofly/thermal_field.py",
        "src/neurofly/light_chase.py",
        "src/neurofly/environment_adapter.py",
        "src/neurofly/platform_server.py",
        "src/neurofly/learning_control_study.py",
        "src/neurofly/runtime_forced_crash_recovery.py",
        "src/neurofly/light_chase_real_smoke.py",
        "site/platform.html",
        "site/platform.css",
        "site/platform.js",
        ".github/workflows/learning-control-study.yml",
        ".github/workflows/runtime-forced-crash-recovery.yml",
        ".github/workflows/light-chase-real-malecns-smoke.yml",
    ]
    assert all((ROOT / path).is_file() for path in required)


def test_v1_candidate_runs_both_environment_factories() -> None:
    maze = make_environment_adapter("maze", seed=109)
    light = make_environment_adapter("light", seed=109)

    assert maze.model == "neurofly-maze-chase-v0.1"
    assert light.model == "neurofly-light-chase-v0.1"


def test_thermosensation_remains_engineering_proxy_only() -> None:
    payload = thermal_change_sensation(temperature_delta_c=0.25)

    assert payload["engineering_proxy"] is True
    assert payload["biological_current_calibrated"] is False
    assert payload["absolute_temperature_exposed"] is False
    assert payload["target_temperature_exposed"] is False
