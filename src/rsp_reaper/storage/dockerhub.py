# Enough of the Docker Hub API to authenticate, to list images, to get
# image digests and tags, and to delete images.

from ..models.image import Image, DATEFMT

import asyncio
import datetime
import httpx
import json
import structlog

LATEST_TAGS = ("latest", "latest_release", "latest_weekly", "latest_daily")

class DockerHubClient(httpx.Client):

    def __init__(self, namespace: str, repository: str) -> None:
        super().__init__()
        self.headers["content-type"] = "application/json"
        self._url = "https://hub.docker.com"
        self._namespace=namespace
        self._repository=repository
        self._auth: str|None = None
        self._images: dict[str,Image] = dict()
        self._logger = structlog.get_logger()

    def authenticate(self, username: str, password: str) -> None:
        url = f"{self._url}/v2/users/login"
        auth = { "username": username,
                 "password": password }
        r = self.post(url, json=auth)
        r.raise_for_status()  # Maybe we'll do 2fa sometime?
        self._logger.info(f"Authenticated user {username} to Docker Hub")
        self.headers["authorization"] = f"Bearer {r.json()['token']}"

    def scan_repo(self) -> None:
        next_page = (
            f"{self._url}/v2/namespaces/{self._namespace}/repositories/"
            f"{self._repository}/tags"
        )
        params = { "page_size": 100 }
        while next_page:
            self._logger.debug(f"GET {next_page}")
            r = self.get(next_page, params=params)
            r.raise_for_status()
            obj = r.json()
            results = obj["results"]
            for res in results:
                tag=res["name"]
                if tag in LATEST_TAGS:
                    # ignore all of these: they're just clutter.
                    continue
                date=res["last_updated"]
                self._logger.debug(f"  name: {tag}")
                images = res["images"]
                for img in images:
                    digest=img["digest"]
                    self._logger.debug(f"    digest: {digest}")
                    self._upsert_image(digest, date, tag)
            next_page = obj["next"]
        
    def _upsert_image(self, digest: str, date: str, tag: str| None) -> None:
        dt = datetime.datetime.strptime(date,DATEFMT)
        if self._images.get(digest, None) and tag:
            if self._images[digest].tags is None:  # empirically happens...
                self._images[digest].tags = set()
            self._images[digest].tags.add(tag)
        else:
            tags: set[str] | None = None
            if tag:
                tags = {tag}
            self._images[digest] = Image(
                digest=digest,
                tags=tags,
                date=dt
            )

    def debug_dump_images(self, filename: str) -> None:
        objs: dict[str, dict[str,str]] = dict()
        for digest in self._images:
            img=self._images[digest]
            obj_img_j = img.toJSON()
            obj_img = json.loads(obj_img_j)
            objs[digest] = obj_img
        with open(filename, "w") as f:
            json.dump(objs,f)

    def debug_load_images(self, filename: str) -> None:
        with open(filename, "r") as f:
            jsons=json.load(f)
        self._images = dict()
        for digest in jsons:
            tags=jsons[digest]["tags"]
            date=jsons[digest]["date"]
            self._images[digest] = Image(
                digest=digest,
                tags=set(tags),
                date=datetime.datetime.strptime(date, DATEFMT)
            )

    def deprecated_delete_untagged(self) -> None:
        ### This API goes away Nov. 15, 2023
        #
        # But it doesn't seem to actually remove anything as of October 20,
        # 2023.
        untagged: list[str] = []
        for digest in self._images:
            img=self._images[digest]
            if not img.tags:
                untagged.append(digest)
        manifests: list[dict[str,str]] = []
        for u in untagged:
            manifests.append({ "repository": self._repository,
                               "digest": u })
        now = datetime.datetime.utcnow()
        then = now - datetime.timedelta(days=30)
        active_from = then.strftime(DATEFMT) + "Z"
        for m in manifests:
            payload = {
                "dry_run": False,
                "active_from": active_from,
                "manifests": [ m ]
            }
            self._logger.debug(f"Deletion payload {payload}")
            r=self.post(
                f"{self._url}/v2/namespaces/{self._namespace}/delete-images",
                json=payload
            )
            r.raise_for_status()
            self._logger.info(f"Image {m['digest']} removed.")

    def deprecated_find_all(self) -> None:
        ### This API goes away Nov. 15, 2023
        next_page = (
            f"{self._url}/v2/namespaces/{self._namespace}"
            f"/repositories/{self._repository}/images"
        )
        params = { "page_size": 100 }
        while next_page:
            self._logger.debug(f"GET {next_page}")
            r = self.get(next_page, params=params)
            r.raise_for_status()
            obj = r.json()
            results = obj["results"]
            for res in results:
                self._logger.debug(f"result: {res}")
                digest = res["digest"]
                date=res["last_pushed"]
                if date is None:
                    # Don't ask me why this is coming back as None
                    date="1984-01-01T00:00:00.000000Z"
                self._logger.debug(f" digest: {digest}")
                self._upsert_image(digest, date, None)
                if res["tags"]:
                    for t in res["tags"]:
                        tag=t["tag"]
                        if tag in LATEST_TAGS:
                            # ignore all of these: they're just clutter.
                            continue
                        self._upsert_image(digest, date, tag)
                        self._logger.debug(f"  name: {tag}")
            next_page = obj["next"]
        
