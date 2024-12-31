"""Configuration for a reaper for a particular container registry."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RegistryAuth:
    """Generic authentication item for a container registry."""

    realm: str|None = None
    username: str|None = None
    password: str|None = None


class LatestSemverKeepers:
    """Number of items to keep for latest major semver release.  Default is
    "do not purge".
    """

    minor: int | None = None
    patch: int | None = None
    build: int | None = None


class OlderSemverKeepers:
    """Number of items to keep for previous major semver releases.  Default is
    "do not purge".
    """

    major: int | None = None
    minor: int | None = None
    patch: int | None = None
    build: int | None = None


@dataclass
class SemverKeepers:
    """Within each of latest_major and older, how many minor versions,
    how many patch versions within each of those, and how many builds of each
    of those, to keep.  Older also has a major version number.  For instance,
    older.major might be 3, and then when version 5.0 came out, you would
    keep some images for the 2.x.y, 3.x.y, and 4.x.y series, but no 1.x images.
    """

    latest_major: LatestSemverKeepers = field(
        default_factory=LatestSemverKeepers
    )
    older: OlderSemverKeepers = field(default_factory=OlderSemverKeepers)


@dataclass
class RSPKeepers:
    """Aliases are never purged.  Default for everything else is "do not
    purge".
    """

    release: int | None = None
    weekly: int | None = None
    daily: int | None = None
    release_candidate: int | None = None
    experimental: int | None = None
    unknown: int | None = None


@dataclass
class KeepPolicy:
    """How many of each image category to keep.  `-1` or `None` means
    "don't reap that category at all".  `0` means "purge them all".
    The default is to purge nothing.
    """

    untagged: int | None = None
    semver: SemverKeepers | None = field(default_factory=SemverKeepers)
    rsp: RSPKeepers | None = field(default_factory=RSPKeepers)


@dataclass
class RegistryConfig:
    """Configuration to talk to a particular container registry."""

    registry: str  # URL of registry host
    owner: str  # Usually repo owner; at GAR, project ID
    repository: str  # Repository name, e.g. "sciplat-lab"
    category: str
    keep: KeepPolicy
    namespace: str | None = None  # Intermediate layer if any; GAR: "sciplat"
    auth: RegistryAuth | None = None
    dry_run: bool = True
    debug: bool = True
    input_file: Path | None = None


@dataclass
class Config:
    """Configuration for multiple registries."""

    registries: list[RegistryConfig]
