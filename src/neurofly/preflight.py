from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .brain_runtime import brain_status

GIB = 1024 ** 3
RECOMMENDED_RAM_GIB = 16.0
LOW_MEMORY_GUARD_GIB = 12.0
RECOMMENDED_FREE_DISK_GIB = 20.0


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    ok: bool
    required: bool
    detail: str


def _total_memory_bytes() -> int | None:
    try:
        if sys.platform == "darwin":
            import subprocess

            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages) * int(page_size)
    except Exception:
        return None


def _disk_probe(path: Path) -> tuple[Path, float | None]:
    probe = path.expanduser().resolve()
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        free = shutil.disk_usage(probe).free / GIB
    except Exception:
        free = None
    return probe, free


def collect_preflight(*, data_dir: str | Path | None = None) -> dict[str, Any]:
    data_path = Path(data_dir or os.environ.get("STONKFLY_DATA", "data"))
    probe, disk_free = _disk_probe(data_path)
    memory_bytes = _total_memory_bytes()
    memory_gib = None if memory_bytes is None else memory_bytes / GIB
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    installed = importlib.util.find_spec("stonkfly") is not None
    brain = brain_status() if installed else {
        "installed": False,
        "prepared": False,
        "error": "stonkfly package is not installed",
    }

    checks = [
        PreflightCheck(
            "python",
            sys.version_info >= (3, 11),
            True,
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        PreflightCheck(
            "compiler",
            compiler is not None,
            True,
            compiler or "No C++17 compiler found in PATH",
        ),
        PreflightCheck(
            "stonkfly",
            installed,
            True,
            "pinned optional dependency importable" if installed else "install with pip install -e '.[stonkfly]'",
        ),
        PreflightCheck(
            "prepared_graph",
            bool(brain.get("prepared")),
            True,
            (
                f"{brain.get('neurons')} neurons / {brain.get('directed_edges')} directed edges"
                if brain.get("prepared")
                else str(brain.get("error") or "run python -m stonkfly prepare")
            ),
        ),
        PreflightCheck(
            "memory_recommended",
            memory_gib is not None and memory_gib >= RECOMMENDED_RAM_GIB,
            False,
            (
                f"{memory_gib:.1f} GiB detected; {RECOMMENDED_RAM_GIB:.0f} GiB recommended"
                if memory_gib is not None
                else "Unable to detect total memory"
            ),
        ),
        PreflightCheck(
            "disk_recommended",
            disk_free is not None and disk_free >= RECOMMENDED_FREE_DISK_GIB,
            False,
            (
                f"{disk_free:.1f} GiB free at {probe}; {RECOMMENDED_FREE_DISK_GIB:.0f} GiB recommended"
                if disk_free is not None
                else f"Unable to inspect free disk at {probe}"
            ),
        ),
    ]

    return {
        "ready": all(check.ok for check in checks if check.required),
        "low_memory_guard": memory_gib is not None and memory_gib < LOW_MEMORY_GUARD_GIB,
        "recommended_ram_gib": RECOMMENDED_RAM_GIB,
        "recommended_free_disk_gib": RECOMMENDED_FREE_DISK_GIB,
        "data_dir": str(data_path.expanduser().resolve()),
        "memory_gib": None if memory_gib is None else round(memory_gib, 2),
        "disk_free_gib": None if disk_free is None else round(disk_free, 2),
        "brain": brain,
        "checks": [asdict(check) for check in checks],
    }
