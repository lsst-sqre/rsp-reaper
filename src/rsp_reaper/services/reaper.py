"""Provides reaping services for a Container Registry configuration."""

import datetime
import logging
import os

import durations
import structlog

from ..config import RegistryAuth, RegistryConfig
from ..models.image import Image, ImageVersionClass
from ..models.registry_category import RegistryCategory
from ..storage.dockerhub import DockerHubClient
from ..storage.gar import GARClient
from ..storage.ghcr import GhcrClient
from ..storage.registry import ContainerRegistryClient


class Reaper:
    """Provides the mechanism to implement an image retention policy."""

    def __init__(self, cfg: RegistryConfig) -> None:

        # Establish debugging and dry-run first.
        self._debug = cfg.debug
        self._dry_run = cfg.dry_run

        log_level = logging.DEBUG if self._debug else logging.INFO
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(log_level)
        )
        # Set up logging
        self._logger = structlog.get_logger()
        self._logger.debug("Initialized logging")

        # Common fields
        self._registry = cfg.registry
        self._owner = cfg.owner
        self._repository = cfg.repository
        self._namespace = cfg.namespace

        # Validate category
        categories = [x.value for x in RegistryCategory]
        if cfg.category not in categories:
            raise ValueError(f"{cfg.category} not in {categories}")
        self._category = cfg.category
        self._auth = RegistryAuth(realm=cfg.registry)

        self._storage: ContainerRegistryClient | None = None
        match self._category:
            case RegistryCategory.DOCKERHUB.value:
                self._storage = DockerHubClient(cfg=cfg)
                self._auth.username = os.getenv("DOCKERHUB_USER")
                self._auth.password = os.getenv("DOCKERHUB_PASSWORD")
            case RegistryCategory.GAR.value:
                self._storage = GARClient(cfg=cfg)
            case RegistryCategory.GHCR.value:
                self._auth.password = os.getenv("GHCR_TOKEN")
                self._storage = GhcrClient(cfg=cfg)
            case _:
                raise NotImplementedError(
                    f"Storage driver for {self._category} not implemented yet"
                )
        vclasses = [x.value.lower() for x in ImageVersionClass]
        if cfg.image_version_class not in vclasses:
            raise ValueError(
                f"Image version class '{cfg.image_version_class}' not in"
                f"{vclasses}"
            )
        self._image_version_class = cfg.image_version_class
        self._keep_policy = cfg.keep

        if not cfg.input_file:
            # We don't have preloaded data, so run a repo scan.
            self._storage.authenticate(self._auth)
            self._storage.scan_repo()

        self._storage.categorize()
        self._categorized = self._storage.categorized_images

    def plan(self) -> dict[str, Image]:
        """Use the KeepPolicy to plan a set of images to delete."""
        if self._image_version_class == ImageVersionClass.RSP.value:
            return self._plan_rsp()
        elif self._image_version_class == ImageVersionClass.SEMVER.value:
            return self._plan_semver()
        else:
            return self._plan_untagged()

    def _plan_semver(self) -> dict[str, Image]:
        raise NotImplementedError("Semver image retention not yet implemented")

    def _plan_rsp(self) -> dict[str, Image]:
        retval: dict[str, Image] = {}
        kp = self._keep_policy.rsp
        if kp is None:
            return self._plan_untagged()
        for img_type in (
            "release",
            "weekly",
            "daily",
            "release_candidate",
            "experimental",
            "unknown",
        ):
            imgs = self._categorized.rsp[img_type]
            match img_type:
                case "release":
                    pol = kp.release
                case "weekly":
                    pol = kp.weekly
                case "daily":
                    pol = kp.daily
                case "release_candidate":
                    pol = kp.release_candidate
                case "experimental":
                    pol = kp.experimental
                case "unknown":
                    pol = kp.unknown
                case _:
                    raise NotImplementedError(
                        f"Don't know what to do with img_type '{img_type}'"
                    )

            if pol.number is None:
                if pol.age is not None:
                    seconds = durations.parse(pol.age)
                    if seconds is not None:
                        retval.update(
                            self._plan_age(seconds=seconds, imgs=imgs)
                        )
            elif pol.number >= 0:
                retval.update(
                    self._plan_number(keep_count=pol.number, imgs=imgs)
                )
        retval.update(self._plan_untagged())
        return retval

    def _plan_untagged(self) -> dict[str, Image]:
        if self._keep_policy.untagged.number is None:
            if self._keep_policy.untagged.age is None:
                return {}
            seconds = durations.parse(self._keep_policy.untagged.age)
            if seconds is None:
                return {}
            return self._plan_age(
                seconds=seconds, imgs=self._categorized.untagged
            )
        if self._keep_policy.untagged.number < 0:
            return {}
        return self._plan_number(
            keep_count=self._keep_policy.untagged.number,
            imgs=self._categorized.untagged,
        )

    def _plan_age(
        self, seconds: float, imgs: dict[str, Image]
    ) -> dict[str, Image]:
        retval: dict[str, Image] = {}
        now = datetime.datetime.now(tz=datetime.UTC)
        age = datetime.timedelta(seconds=seconds)
        cutoff = now - age

        for dig in imgs:
            img = self._categorized.untagged[dig]
            if img.date is None:
                self._logger.warning(f"Image '{dig}' has no date")
                continue
            if img.date < cutoff:
                self._logger.debug(
                    f"Selecting image '{dig}' for reaping: "
                    f"{img.date.isoformat()} is older than cutoff "
                    f"{cutoff.isoformat()}"
                )
                retval[dig] = img
            else:
                self._logger.debug(
                    f"Image '{dig}' has date {img.date.isoformat()}, "
                    f"which is newer than cutoff {cutoff.isoformat()}"
                )
        return retval

    def _plan_number(
        self, keep_count: int, imgs: dict[str, Image]
    ) -> dict[str, Image]:
        # Categorized images are already sorted
        return {x.digest: x for x in list(imgs.values())[keep_count:]}
