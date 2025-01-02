"""Configuration for a reaper for a particular container registry."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RegistryAuth:
    """Generic authentication item for a container registry."""

    realm: str | None = None
    username: str | None = None
    password: str | None = None


@dataclass
class IndividualKeepPolicy:
    """The policy has both a 'number' and an 'age' field.  'number'
    means keep that many of whatever image class this is attached to.
    `-1` or `None` means "do not reap that class at all". and `0`
    means "purge them all".  'age' means keep anything that is the
    specified duration or less.  Durations are strings as accepted by
    https://github.com/wroberts/pytimeparse and once again `None` or
    the empty string means "do not reap that class at all".

    You should specify only one of these.  If both are specified, 'number'
    will win.
    """

    age: str | None = None
    number: int | None = None


class LatestSemverKeepers:
    """How to choose items to keep for latest major semver release.
    Default is "do not purge".
    """

    minor: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    patch: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    build: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)


class OlderSemverKeepers:
    """How to choose items to keep for previous major semver releases.
    Default is "do not purge".
    """

    major: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    minor: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    patch: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    build: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)


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

    release: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    weekly: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    daily: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)
    release_candidate: IndividualKeepPolicy = field(
        default_factory=IndividualKeepPolicy
    )
    experimental: IndividualKeepPolicy = field(
        default_factory=IndividualKeepPolicy
    )
    unknown: IndividualKeepPolicy = field(default_factory=IndividualKeepPolicy)


@dataclass
class KeepPolicy:
    """How to choose which images within each image category to keep.
    The default is to purge nothing.
    """

    untagged: IndividualKeepPolicy = field(
        default_factory=IndividualKeepPolicy
    )
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
    image_version_class: str = "rsp"
    namespace: str | None = None  # Intermediate layer if any; GAR: "sciplat"
    auth: RegistryAuth | None = None
    dry_run: bool = True
    debug: bool = True
    input_file: Path | None = None


@dataclass
class Config:
    """Configuration for multiple registries."""

    registries: list[RegistryConfig]
