from .rsptag import RSPImageType
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Self
import datetime
import json
import semver

DATEFMT = "%Y-%m-%dT%H:%M:%S.%f%z"


@dataclass
class Image:
    """Class representing the things about an OCI image we care about."""

    digest: str
    tags: set[str] = field(default_factory=set)
    date: datetime.datetime | None = None

    def to_dict(self):
        # Differs from asdict, in that set and datetime aren't
        # JSON-serializable, so we make them a list and a string.
        self_dict = asdict(self)
        list_tags: list[str] = []
        if self.tags:
            list_tags = list(self.tags)
        self_dict["tags"] = list_tags
        self_dict["date"] = self.date.strftime(DATEFMT)
        return self_dict

    def toJSON(self) -> str:
        return json.dumps(self_to_dict())

    @classmethod
    def fromJSON(cls, inp: str) -> Self:
        self_dict = json.loads(inp)
        return cls(
            digest=self_dict["digest"],
            tags=set(self_dict["tags"]),
            date=datetime.datetime.strptime(self_dict["date"], DATEFMT),
        )


@dataclass
class SemverImage(Image):
    """The image tags can be mapped to (a single) semantic version."""

    semantic_version: semver.Version | None = None


@dataclass
class RSPImage(Image):
    """The image tags can be mapped to (a single) RSP Image type."""

    rsp_image_type: RSPImageType | None = None
