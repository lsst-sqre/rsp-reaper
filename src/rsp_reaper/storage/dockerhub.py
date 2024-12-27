"""Minimalist function set of the Docker Hub API.

We must be able to list images, to get image digests and tags, and to
delete images.
"""

import datetime
import json
from pathlib import Path

import httpx
import structlog

from ..models.image import DATEFMT, Image, JSONImage
from ..models.registry_category import RegistryCategory
from .registry import ContainerRegistryClient

LATEST_TAGS = ("latest", "latest_release", "latest_weekly", "latest_daily")


class DockerHubClient(ContainerRegistryClient, httpx.Client):
    """Client for talking to docker.io / hub.docker.com."""

    def __init__(
        self, namespace: str, repository: str, *, dry_run: bool = False
    ) -> None:
        super().__init__()
        self.headers["content-type"] = "application/json"
        self._url = "https://hub.docker.com"
        self._namespace = namespace
        self._repository = repository
        self._images: dict[str, Image] = {}
        self._logger = structlog.get_logger()
        self._dry_run = dry_run

    def authenticate(self, username: str, password: str) -> None:
        url = f"{self._url}/v2/users/login"
        auth = {"username": username, "password": password}
        r = self.post(url, json=auth)
        r.raise_for_status()  # Maybe we'll do 2fa sometime?
        self._logger.info(f"Authenticated user {username} to Docker Hub")
        self.headers["authorization"] = f"Bearer {r.json()['token']}"

    def scan_repo(self) -> None:
        next_page = (
            f"{self._url}/v2/namespaces/{self._namespace}/repositories/"
            f"{self._repository}/tags"
        )
        page_size = 100
        count = 0
        params = {"page_size": page_size}
        while next_page:
            self._logger.debug(
                f"Requesting {self._namespace}/{self._repository}: images "
                f"{count*page_size + 1}-{(count+1) * page_size}"
            )
            if count > 0:
                params["page"] = count + 1
            r = self.get(next_page, params=params)
            r.raise_for_status()
            obj = r.json()
            next_page = obj["next"]
            results = obj["results"]
            for res in results:
                tag = res["name"]
                if tag in LATEST_TAGS:
                    # ignore all of these: they're just clutter.
                    continue
                date = res["last_updated"]
                images = res["images"]
                for img in images:
                    digest = img["digest"]
                    self._upsert_image(digest, date, tag)
            count += 1
        self._logger.debug(f"Found {len(list(self._images.keys()))} images")

    def _upsert_image(self, digest: str, date: str, tag: str | None) -> None:
        dt = datetime.datetime.strptime(date, DATEFMT).astimezone(datetime.UTC)
        if self._images.get(digest, None) and tag:
            if self._images[digest].tags is None:  # empirically happens...
                self._images[digest].tags = set()
            self._images[digest].tags.add(tag)
        else:
            tags = {tag} if tag else set()
            self._images[digest] = Image(digest=digest, tags=tags, date=dt)

    def debug_dump_images(self, outputfile: Path) -> None:
        objs: dict[str, JSONImage] = {}
        for digest in self._images:
            img = self._images[digest]
            obj_img = img.to_dict()
            objs[digest] = obj_img
        dd: dict[str, dict[str, str] | dict[str, JSONImage]] = {
            "metadata": {"category": RegistryCategory.DOCKERHUB.value},
            "data": objs,
        }
        outputfile.write_text(json.dumps(dd, indent=2))

    def debug_load_images(self, inputfile: Path) -> None:
        inp = json.loads(inputfile.read_text())
        if inp["metadata"]["category"] != RegistryCategory.DOCKERHUB.value:
            raise ValueError(
                f"Dump is from {inp['metadata']['category']}, "
                f"not {RegistryCategory.DOCKERHUB.value}"
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

    def _find_untagged(self) -> list[Image]:
        untagged: list[Image] = []
        for digest in self._images:
            img = self._images[digest]
            if not img.tags:
                untagged.append(img)
        return untagged

    def deprecated_delete_untagged(self) -> None:
        """Delete all untagged images."""
        ### This API goes away Nov. 15, 2023.  Possibly December 11.
        #
        # But it doesn't seem to actually remove anything as of October 20,
        # 2023.
        manifests = [
            {"repository": self._repository, "digest": x.digest}
            for x in self._find_untagged()
        ]
        now = datetime.datetime.now(tz=datetime.UTC)
        now - datetime.timedelta(days=30)
        count = 0
        dry = ""
        if self._dry_run:
            dry = " (not really)"
        for m in manifests:
            payload = {
                "dry_run": self._dry_run,
                "manifests": [m],
            }
            r = self.post(
                f"{self._url}/v2/namespaces/{self._namespace}/delete-images",
                json=payload,
            )
            r.raise_for_status()
            self._logger.debug(f"Image {m['digest']} deleted{dry}")
            count += 1
        self._logger.debug(f"Deleted {count} images{dry}")

    def deprecated_find_all(self) -> None:
        ### This API goes away Nov. 15, 2023.  Possibly December 11.
        next_page = (
            f"{self._url}/v2/namespaces/{self._namespace}"
            f"/repositories/{self._repository}/images"
        )
        page_size = 100
        params = {"page_size": page_size}
        count = 0
        while next_page:
            self._logger.debug(
                f"Requesting {self._namespace}/{self._repository}: images "
                f"{count*page_size + 1}-{(count+1) * page_size}"
            )
            r = self.get(next_page, params=params)
            r.raise_for_status()
            obj = r.json()
            results = obj["results"]
            for res in results:
                digest = res["digest"]
                date = res["last_pushed"]
                if date is None:
                    # Don't ask me why this is coming back as None
                    date = "1984-01-01T00:00:00.000000Z"
                self._upsert_image(digest, date, None)
                if res["tags"]:
                    for t in res["tags"]:
                        tag = t["tag"]
                        if tag in LATEST_TAGS:
                            # ignore all of these: they're just clutter.
                            continue
                        self._upsert_image(digest, date, tag)
            next_page = obj["next"]
            count += 1
        self._logger.debug(f"Found {len(list(self._images.keys()))} images")
