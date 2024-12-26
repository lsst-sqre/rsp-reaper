"""Model for necessary information about container images."""

import datetime
import json
from dataclasses import asdict, dataclass, field
from typing import Self

import semver

from .rsptag import RSPImageType

DATEFMT = "%Y-%m-%dT%H:%M:%S.%f%z"


@dataclass
class Image:
    """Class representing the things about an OCI image we care about."""

    digest: str
    tags: set[str] = field(default_factory=set)
    date: datetime.datetime | None = None

    def to_dict(self) -> dict[str, str | list[str]]:
        # Differs from asdict, in that set and datetime aren't
        # JSON-serializable, so we make them a list and a string.
        self_dict = asdict(self)
        list_tags: list[str] = []
        if self.tags:
            list_tags = list(self.tags)
        self_dict["tags"] = list_tags
        self_dict["date"] = self.date.strftime(DATEFMT)
        return self_dict

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, inp: str) -> Self:
        self_dict = json.loads(inp)
        return cls(
            digest=self_dict["digest"],
            tags=set(self_dict["tags"]),
            date=datetime.datetime.strptime(
                self_dict["date"], DATEFMT
            ).replace(tzinfo=datetime.tz.utc),
        )


@dataclass
class SemverImage(Image):
    """The image tags can be mapped to (a single) semantic version."""

    semantic_version: semver.Version | None = None


@dataclass
class RSPImage(Image):
    """The image tags can be mapped to (a single) RSP Image type."""

    rsp_image_type: RSPImageType | None = None
