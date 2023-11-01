"""Storage driver for ghcr.io package repository."""

import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog

from ..models.image import DATEFMT, Image
from ..models.registry_category import RegistryCategory


@dataclass
class GhcrImage:
    id: int
    image: Image


class GhcrClient(httpx.Client):
    def __init__(self, namespace: str, repository: str) -> None:
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
        self._auth: str | None = None
        self._image_by_digest: dict[str, GhcrImage] = {}
        self._image_by_id: dict[str, Image] = {}
        self._logger = structlog.get_logger()

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
            img = Image(digest=digest, tags=tags, date=date)
            ghcr_image = GhcrImage(image=img, id=id)
            self._image_by_digest[digest] = ghcr_image
            self._image_by_id[id] = img
        self._logger.debug(
            f"Found {len(list(self._image_by_id.keys()))} images"
        )

    def debug_dump_images(self, filename: str) -> None:
        objs: dict[str, Any] = {}
        for digest in self._image_by_digest:
            img = self._image_by_digest[digest].image
            id = self._image_by_digest[digest].id
            obj_img = img.to_dict()
            objs[digest] = {}
            objs[digest]["image"] = obj_img
            objs[digest]["id"] = id
        dd: dict[str, Any] = {
            "metadata": {"category": RegistryCategory.GHCR.value},
            "data": objs,
        }
        with Path.open(filename, "w") as f:
            json.dump(dd, f, indent=2)

    def debug_load_images(self, filename: str) -> None:
        with Path.open(filename) as f:
            inp = json.load(f)
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
            )
            ghcr_img = GhcrImage(id=id, image=Image)
            self._image_by_digest[digest] = ghcr_img
            self._image_by_id[id] = img

    def _find_untagged(self) -> list[GhcrImage]:
        ret: list[GhcrImage] = []
        for dig in self._image_by_digest:
            g_img = self._image_by_digest[dig]
            if not g_img.image.tags:
                ret.append(g_img)
        return ret

    def delete_untagged(self) -> None:
        """Delete all untagged images."""
        untagged = self._find_untagged()
        count = 0
        for u in untagged:
            url = (
                f"{self._url}/orgs/{self._namespace}/packages"
                f"/container/{self._repository}/versions/{u.id}"
            )
            r = self.delete(url)
            r.raise_for_status()
            self._logger.debug(f"Image {u.image.digest} deleted")
            count += 1
        self._logger.debug(f"Deleted {count} images")
