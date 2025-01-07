"""Storage client for Google Artifact Registry."""

import datetime
import json
from pathlib import Path
from typing import cast

from google.cloud.artifactregistry_v1 import (
    ArtifactRegistryClient,
    ListDockerImagesRequest,
)
from google.cloud.artifactregistry_v1.types import DockerImage

from ..config import RegistryAuth, RegistryConfig
from ..models.image import Image, ImageSpec, JSONImage
from ..models.registry_category import RegistryCategory
from .registry import ContainerRegistryClient


class GARClient(ContainerRegistryClient):
    """Client for Google Artifact Registry."""

    def __init__(self, cfg: RegistryConfig) -> None:
        if cfg.category != RegistryCategory.GAR:
            raise ValueError(
                "GAR registry client must have value "
                f"'{RegistryCategory.GAR.value}', not '{cfg.category.value}'"
            )
        self._category = cfg.category
        super()._extract_registry_config(cfg)
        gar_loc = "-docker.pkg.dev/"
        if not self._registry.endswith(gar_loc):
            raise ValueError(
                f"GAR registry location ('{self._registry}') must "
                f"end with '{gar_loc}'"
            )
        location = self._registry[len("https://") : -(len(gar_loc))]

        self._parent: str = (
            f"projects/{self._owner}/locations/{location}"
            f"/repositories/{self._namespace}"
        )
        self._path: str = f"{self._owner}/{self._namespace}/{self._repository}"
        self._client: ArtifactRegistryClient = ArtifactRegistryClient()

    def authenticate(self, auth: RegistryAuth) -> None:
        """In production, we will use Workload Identity.

        For testing, we will use application default credentials.
        """

    def scan_repo(self) -> None:
        images: list[DockerImage] = []
        page_size = 100
        request = ListDockerImagesRequest(
            parent=self._parent, page_size=page_size
        )
        count = 0
        while True:
            self._logger.debug(
                f"Requesting {self._owner}/{self._namespace}/"
                f"{self._repository}: images "
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
        count = 0
        for digest in jsons:
            obj = cast(JSONImage, jsons[digest])
            self._images[digest] = Image.from_json(obj)
            count += 1
        self._logger.debug(f"Ingested {count} image{ 's' if count>1 else ''}")

    def _image_to_name(self, img: Image) -> str:
        return (
            f"{self._parent}/packages/{self._repository}/versions/{img.digest}"
        )

    def delete_images(self, inp: ImageSpec) -> None:
        images = self._canonicalize_image_map(inp)
        # Not implemented yet
        _ = images
