"""Model for necessary information about container images."""

import datetime
import json
from dataclasses import asdict, dataclass, field
from typing import Self, cast

import semver

from .rsptag import RSPImageType

DATEFMT = "%Y-%m-%dT%H:%M:%S.%f%z"

type JSONImage = dict[str, str | int | list[str] | None]


@dataclass
class Image:
    """Class representing the things about an OCI image we care about.

    This actually has to be a superset of those things, and some will be
    optional.  Case in point: you need the image ID (an integer) to do
    package deletion at ghcr.io.  But at other sites, there's no such
    thing.
    """

    digest: str
    tags: set[str] = field(default_factory=set)
    date: datetime.datetime | None = None
    id: int | None = None

    def to_dict(self) -> JSONImage:
        # Differs from asdict, in that set and datetime aren't
        # JSON-serializable, so we make them a list and a string.
        self_dict = asdict(self)
        list_tags: list[str] = []
        if self.tags:
            list_tags = list(self.tags)
        self_dict["tags"] = list_tags
        if self.date is None:
            self_dict["date"] = None
        else:
            self_dict["date"] = self.date.strftime(DATEFMT)
        return self_dict

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, inp: JSONImage | str) -> Self:
        """Much painful assertion that each field is the right type."""
        if isinstance(inp, str):
            obj = json.loads(inp)
            inp = cast(JSONImage, obj)
        new_date: datetime.datetime | None = None
        if not isinstance(inp["digest"], str):
            raise TypeError(f"'digest' field of {inp} must be a string")
        if inp["date"] and isinstance(inp["date"], str):
            new_date = datetime.datetime.strptime(
                inp["date"], DATEFMT
            ).replace(tzinfo=datetime.UTC)
        new_tags = set()
        t_s = inp["tags"]
        if t_s and not isinstance(t_s, str) and not isinstance(t_s, int):
            new_tags = set(t_s)
        new_id: int | None = None
        i_i = inp["id"]
        if i_i and isinstance(i_i, int):
            new_id = i_i
        return cls(
            digest=inp["digest"], tags=new_tags, date=new_date, id=new_id
        )


@dataclass
class SemverImage(Image):
    """The image tags can be mapped to (a single) semantic version."""

    semantic_version: semver.Version | None = None


@dataclass
class RSPImage(Image):
    """The image tags can be mapped to (a single) RSP Image type."""

    rsp_image_type: RSPImageType | None = None
