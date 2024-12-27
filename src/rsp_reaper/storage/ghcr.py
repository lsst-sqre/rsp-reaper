"""Storage driver for ghcr.io package registry."""

import datetime
import json
from pathlib import Path
from typing import Any

import httpx
import structlog

from ..models.image import DATEFMT, Image, JSONImage
from ..models.registry_category import RegistryCategory
from .registry import ContainerRegistryClient


class GhcrClient(ContainerRegistryClient, httpx.Client):
    """Storage client for communication with ghcr.io."""

    def __init__(
        self, namespace: str, repository: str, *, dry_run: bool = False
    ) -> None:
        super().__init__()
        self.headers.update(
            {
                "content-type": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self._url = "https://api.github.com"
        self._namespace = namespace
        self._repository = repository
        self._image_by_digest: dict[str, Image] = {}
        self._image_by_id: dict[str, Image] = {}
        self._logger = structlog.get_logger()
        self._dry_run = dry_run

    def authenticate(self, token: str) -> None:
        self.headers["authorization"] = f"Bearer {token}"

    def scan_repo(self) -> None:
        url = (
            f"{self._url}/orgs/{self._namespace}/packages"
            f"/container/{self._repository}/versions"
        )
        page_size = 100
        params = {"per_page": page_size}
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            self._logger.debug(
                f"Requesting {self._namespace}/{self._repository}: images "
                f"{(page -1) *page_size + 1}-{page * page_size}"
            )
            params["page"] = page
            r = self.get(url, params=params)
            r.raise_for_status()
            imgs = r.json()
            if len(imgs) == 0:
                break
            results.extend(imgs)
            page += 1
        for i in results:
            digest = i["name"]
            id = i["id"]
            tags = i["metadata"]["container"]["tags"]
            # GHCR doesn't do fractional seconds, but does keep date in UTC
            date = datetime.datetime.strptime(
                f"{i['updated_at'][:-1]}.000000Z", DATEFMT
            ).astimezone(tz=datetime.UTC)
            img = Image(digest=digest, tags=tags, date=date, id=id)
            self._image_by_digest[digest] = img
            self._image_by_id[id] = img
        self._logger.debug(
            f"Found {len(list(self._image_by_id.keys()))} images"
        )

    def debug_dump_images(self, outputfile: Path) -> None:
        objs: dict[str, JSONImage] = {}
        for digest in self._image_by_digest:
            img = self._image_by_digest[digest]
            obj_img = img.to_dict()
            objs[digest] = obj_img
        dd: dict[str, dict[str, str] | dict[str, JSONImage]] = {
            "metadata": {"category": RegistryCategory.GHCR.value},
            "data": objs,
        }
        outputfile.write_text(json.dumps(dd, indent=2))

    def debug_load_images(self, inputfile: Path) -> None:
        inp = json.loads(inputfile.read_text())
        if inp["metadata"]["category"] != RegistryCategory.GHCR.value:
            raise ValueError(
                f"Dump is from {inp['metadata']['category']}, "
                f"not {RegistryCategory.GHCR.value}"
            )
        jsons = inp["data"]
        self._image_by_digest = {}
        self._image_by_id = {}
        for digest in jsons:
            tags = jsons[digest]["image"]["tags"]
            date = jsons[digest]["image"]["date"]
            id = jsons[digest]["id"]
            img = Image(
                digest=digest,
                tags=set(tags),
                date=datetime.datetime.strptime(date, DATEFMT).astimezone(
                    datetime.UTC
                ),
                id=id,
            )
            self._image_by_digest[digest] = img
            self._image_by_id[id] = img

    def _find_untagged(self) -> list[Image]:
        ret: list[Image] = []
        for dig in self._image_by_digest:
            g_img = self._image_by_digest[dig]
            if not g_img.tags:
                ret.append(g_img)
        return ret

    def delete_untagged(self) -> None:
        """Delete all untagged images."""
        untagged = self._find_untagged()
        count = 0
        dry = ""
        if self._dry_run:
            dry = " (not really)"
        for u in untagged:
            url = (
                f"{self._url}/orgs/{self._namespace}/packages"
                f"/container/{self._repository}/versions/{u.id}"
            )
            if not self._dry_run:
                r = self.delete(url)
                r.raise_for_status()
            self._logger.debug(f"Image {u.digest} deleted{dry}")
            count += 1
        self._logger.debug(f"Deleted {count} images{dry}")
