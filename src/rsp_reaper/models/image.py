from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Self
import datetime
import json
import semver

DATEFMT="%Y-%m-%dT%H:%M:%S.%f%z"

class RSPImageType(Enum):
    """The type (generally, release series) of the identified image.

    This is RSP-specific and taken from jupyterlab-controller.  We can
    also work with semantic versioning.
    """

    ALIAS = "Alias"
    RELEASE = "Release"
    WEEKLY = "Weekly"
    DAILY = "Daily"
    CANDIDATE = "Release Candidate"
    EXPERIMENTAL = "Experimental"
    UNKNOWN = "Unknown"

@dataclass 
class Image:
    """Class representing the things about an OCI image we care about."""
    digest: str
    tags: set[str] = field(default_factory=set)
    date: datetime.datetime | None = None

    def toJSON(self) -> str:
        self_dict = asdict(self)
        list_tags: list[str] = []
        if self.tags:
            list_tags = list(self.tags)
        self_dict["tags"] = list_tags
        self_dict["date"] = self.date.strftime(DATEFMT)
        return json.dumps(self_dict)

    @classmethod
    def fromJSON(cls, inp: str) -> Self:
        self_dict=json.loads(inp)
        return cls(
            digest=self_dict["digest"],
            tags=set(self_dict["tags"]),
            date=datetime.datetime.strptime(self_dict["date"], DATEFMT)
        )
    
        

@dataclass
class SemverImage(Image):
    """The image tags can be mapped to (a single) semantic version."""
    semantic_version: semver.Version | None = None

@dataclass
class RSPImage(Image):
    """The image tags can be mapped to (a single) RSP Image type."""
    rsp_image_type: RSPImageType | None = None
