"""Storage client for Google Artifact Registry."""

import datetime
import json
from pathlib import Path

import structlog
from google.cloud.artifactregistry_v1 import (
    ArtifactRegistryClient,
    DeleteVersionRequest,
    ListDockerImagesRequest,
)
from google.cloud.artifactregistry_v1.types import DockerImage

from ..models.image import DATEFMT, Image, JSONImage
from ..models.registry_category import RegistryCategory
from .registry import ContainerRegistryClient


class GARClient(ContainerRegistryClient):
    """Client for Google Artifact Registry.

    We assume we can use application default credentials.  It should be run
    using Workload Identity when it's run for real rather than for testing.
    """

    def __init__(
        self,
        location: str,
        project_id: str,
        repository: str,
        image: str,
        *,
        dry_run: bool = False,
    ) -> None:
        self._location = location
        self._project_id = project_id
        self._repository = repository
        self._image = image
        self._registry = f"{location}-docker.pkg.dev"
        self._parent = (
            f"projects/{project_id}/locations/{location}"
            f"/repositories/{repository}"
        )
        # "path" is what everything else calls a repository
        self._path = f"{project_id}/{repository}/{image}"
        self._client = ArtifactRegistryClient()
        self._logger = structlog.get_logger()
        self._images: dict[str, Image] = {}
        self._dry_run = dry_run

    def scan_repo(self) -> None:
        images: list[DockerImage] = []
        page_size = 100
        request = ListDockerImagesRequest(
            parent=self._parent, page_size=page_size
        )
        count = 0
        while True:
            self._logger.debug(
                f"Requesting {self._path}: images "
                f"{count*page_size + 1}-{(count+1) * page_size}"
            )
            resp = self._client.list_docker_images(request=request)
            images.extend(list(resp.docker_images))
            if not resp.next_page_token:
                break
            request = ListDockerImagesRequest(
                parent=self._parent,
                page_token=resp.next_page_token,
                page_size=page_size,
            )
            count += 1
        self._logger.debug(f"Found {len(images)} images")
        self._images = self._gar_to_images(images)

    def _gar_to_images(self, images: list[DockerImage]) -> dict[str, Image]:
        ret: dict[str, Image] = {}
        for img in images:
            ut = img.update_time
            micros = int(ut.nanosecond / 1000)
            dt = datetime.datetime(
                year=ut.year,
                month=ut.month,
                day=ut.day,
                hour=ut.hour,
                minute=ut.minute,
                second=ut.second,
                microsecond=micros,
                tzinfo=datetime.UTC,
            )
            tags = set(img.tags)
            digest = img.name.split("@")[-1]
            ret[digest] = Image(digest=digest, tags=tags, date=dt)
        return ret

    def debug_dump_images(self, outputfile: Path) -> None:
        objs: dict[str, JSONImage] = {}
        for digest in self._images:
            img = self._images[digest]
            obj_img = img.to_dict()
            objs[digest] = obj_img
        dd: dict[str, dict[str, str] | dict[str, JSONImage]] = {
            "metadata": {"category": RegistryCategory.GAR.value},
            "data": objs,
        }
        outputfile.write_text(json.dumps(dd, indent=2))

    def debug_load_images(self, inputfile: Path) -> None:
        inp = json.loads(inputfile.read_text())
        if inp["metadata"]["category"] != RegistryCategory.GAR.value:
            raise ValueError(
                f"Dump is from {inp['metadata']['category']}, "
                f"not {RegistryCategory.GAR.value}"
            )
        jsons = inp["data"]
        self._images = {}
        for digest in jsons:
            tags = jsons[digest]["tags"]
            date = jsons[digest]["date"]
            self._images[digest] = Image(
                digest=digest,
                tags=set(tags),
                date=datetime.datetime.strptime(date, DATEFMT).astimezone(
                    datetime.UTC
                ),
            )

    def _image_to_name(self, img: Image) -> str:
        return f"{self._parent}/packages/{self._image}/versions/{img.digest}"

    def _find_untagged(self) -> list[Image]:
        return [x for x in self._images.values() if not x.tags]

    def delete_untagged(self) -> None:
        """Delete all untagged images."""
        untagged = self._find_untagged()
        count = 0
        dry = ""
        if self._dry_run:
            dry = " (not really)"
        for u in untagged:
            digest = u.digest
            request = DeleteVersionRequest(name=self._image_to_name(u))
            self._logger.debug(f"Deletion request: {request}")
            if not self._dry_run:
                # Don't understand what's wrong with the next line
                operation = self._client.delete_version(request=request)
                self._logger.debug(
                    f"Waiting for deletion of {self._path}@{digest} to finish"
                )
                operation.result()
            count += 1
        self._logger.debug(f"Deleted {count} images{dry}")
