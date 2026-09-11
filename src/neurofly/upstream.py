from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata

STONKFLY_REPOSITORY = "https://github.com/nftechie/stonkfly"
STONKFLY_COMMIT = "78ef3e05ab0fa086032098558d893667068944a0"


@dataclass(frozen=True, slots=True)
class UpstreamStatus:
    name: str
    installed: bool
    version: str | None
    repository: str
    pinned_commit: str


def stonkfly_status() -> UpstreamStatus:
    try:
        version = metadata.version("stonkfly")
    except metadata.PackageNotFoundError:
        version = None

    return UpstreamStatus(
        name="stonkfly",
        installed=version is not None,
        version=version,
        repository=STONKFLY_REPOSITORY,
        pinned_commit=STONKFLY_COMMIT,
    )
