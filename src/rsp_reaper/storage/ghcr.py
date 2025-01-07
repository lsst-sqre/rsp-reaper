"""Storage driver for ghcr.io package registry."""

import datetime
import json
from pathlib import Path
from typing import Any, cast

import httpx

from ..config import RegistryAuth, RegistryConfig
from ..models.image import DATEFMT, Image, ImageSpec, JSONImage
from ..models.registry_category import RegistryCategory
from .registry import ContainerRegistryClient


class GhcrClient(ContainerRegistryClient):
    """Storage client for communication with ghcr.io."""

    def __init__(self, cfg: RegistryConfig) -> None:
        if cfg.category != RegistryCategory.GHCR:
            raise ValueError(
                "GHCR registry client must have value "
                f"'{RegistryCategory.GHCR.value}', not '{cfg.category.value}'"
            )
        super()._extract_registry_config(cfg)
        self._http_client = httpx.Client()
        self._http_client.headers.update(
            {
                "content-type": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self._url = "https://api.github.com"
        self._image_by_id: dict[str, Image] = {}

    def authenticate(self, auth: RegistryAuth) -> None:
        """Use the 'password' field as the token.  Other fields ignored."""
        self._http_client.headers["authorization"] = f"Bearer {auth.password}"

    def scan_repo(self) -> None:
        url = (
            f"{self._url}/orgs/{self._owner}/packages"
            f"/container/{self._repository}/versions"
        )
        page_size = 100
        params = {"per_page": page_size}
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            self._logger.debug(
                f"Requesting {self._owner}/{self._repository}: images "
                f"{(page -1) *page_size + 1}-{page * page_size}"
            )
            params["page"] = page
            r = self._http_client.get(url, params=params)
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
            self._images[digest] = img
            self._image_by_id[id] = img
        self._logger.debug(
            f"Found {len(list(self._image_by_id.keys()))} images"
        )

    def debug_dump_images(self, outputfile: Path) -> None:
        objs: dict[str, JSONImage] = {}
        for digest in self._images:
            img = self._images[digest]
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
        self._images = {}
        self._image_by_id = {}
        for digest in jsons:
            id = jsons[digest]["id"]
            obj = cast(JSONImage, jsons[digest])
            img = Image.from_json(obj)
            self._images[digest] = img
            self._image_by_id[id] = img

    def _find_untagged(self) -> list[Image]:
        ret: list[Image] = []
        for dig in self._images:
            g_img = self._images[dig]
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
                f"{self._url}/orgs/{self._owner}/packages"
                f"/container/{self._repository}/versions/{u.id}"
            )
            if not self._dry_run:
                r = self._http_client.delete(url)
                r.raise_for_status()
            self._logger.debug(f"Image {u.digest} deleted{dry}")
            count += 1
        self._logger.debug(f"Deleted {count} images{dry}")

    def delete_images(self, inp: ImageSpec) -> None:
        images = self._canonicalize_image_map(inp)
        # Not implemented yet
        _ = images
