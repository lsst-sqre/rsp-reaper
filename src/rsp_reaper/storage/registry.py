"""Abstract superclass for container registry clients."""

import logging
from abc import abstractmethod
from pathlib import Path
from typing import cast

import semver
import structlog

from ..config import RegistryAuth, RegistryConfig
from ..models.image import Image, ImageCollection, ImageSpec, ImageVersionClass
from ..models.registry_category import RegistryCategory
from ..models.rsptag import (
    ALIAS_TAGS, RSPImageTag, RSPImageTagCollection, RSPImageType
)


class ContainerRegistryClient:
    """Collection of methods we expect any registry client to provide.

    Note that these are synchronous.  That's on purpose.  You can't really
    do anything until the scan_repo() (or debug_load_images()) completes, so
    there's no point making the generation of the initial map of images
    async.

    The actual image deletion could be done as async methods.  In
    fact, the initial run may take a long time if there are hundreds
    or thousands of images to delete.  However, after that, normally
    you're going to be running this daily, and you will be removing no
    more than a handful of images on any given run.  Whether that
    takes 45 seconds or 51 seconds (scanning the repository will be
    the longest-running task by far) is not particularly important.

    Registries generally rate-limit requests in any event, so blasting out a
    thousand DELETE requests in parallel is not going to work as well as you
    might hope.
    """

    @abstractmethod
    def authenticate(self, auth: RegistryAuth) -> None: ...

    @abstractmethod
    def scan_repo(self) -> None: ...

    @abstractmethod
    def debug_dump_images(self, outputfile: Path) -> None:
        """Write JSON of image map."""
        ...

    @abstractmethod
    def debug_load_images(self, inputfile: Path) -> None:
        """Read image map from JSON."""
        ...

    @abstractmethod
    def delete_images(self, inp: ImageSpec) -> None:
        """Delete one or many images."""
        ...

    def __init__(self, cfg: RegistryConfig) -> None:
        # Only here to get instance fields referenced in non-abstract methods.
        # Generally, redefine these in child classes, because multiple
        # inheritance makes running super().__init__() ugly.
        self._extract_registry_config(cfg)

    def _find_untagged_images(self) -> dict[str, Image]:
        # Return a map of untagged images by digest
        return {x.digest: x for x in self._images.values() if not x.tags}

    def _extract_registry_config(self, cfg: RegistryConfig) -> None:
        # Load the generic items from the registry config

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

        # Initialize empty image map
        self._images: dict[str, Image] = {}
        # Initialize empty categorized image map
        self._categorized_images = ImageCollection()

        # Load inputs if supplied
        if cfg.input_file:
            self.debug_load_images(cfg.input_file)

    def categorize(self, image_version_class: ImageVersionClass) -> None:
        """Run images through the tag interpreter; categorize and sort them."""
        if image_version_class == ImageVersionClass.RSP:
            self._categorize_rsp()
        elif image_version_class == ImageVersionClass.SEMVER:
            self._categorize_semver()
        self._categorize_untagged()
        self._image_version_class = image_version_class

    def _categorize_rsp(self) -> None:
        unsorted: list[Image] = list(self._images.values())
        # Add a single RSP tag to each image
        for img in unsorted:
            raw_tags = list(img.tags)
            collection = RSPImageTagCollection.from_tag_names(
                raw_tags, aliases=ALIAS_TAGS, cycle=None
            )
            rsp_image_tag = collection.best_tag()
            if rsp_image_tag is None:
                # Force an 'UNKNOWN' tag
                t_tag = raw_tags[0] if len(img.tags) > 0 else "unknown"
                rsp_image_tag = RSPImageTag.from_str(t_tag)
            img.rsp_image_tag = rsp_image_tag

        # categorize each image by type
        for typ in RSPImageType:
            key = typ.value.lower().replace(" ", "_")
            self._categorized_images.rsp[key] = {
                x.digest: x
                for x in unsorted
                if x.rsp_image_tag is not None
                and x.rsp_image_tag.image_type == typ
                and x.tags
            }
        # now sort within each type
        for typ in RSPImageType:
            key = typ.value.lower().replace(" ", "_")
            unsorted = list(self._categorized_images.rsp[key].values())
            sorted_img = sorted(unsorted, reverse=True)
            self._categorized_images.rsp[key] = {
                x.digest: x for x in sorted_img
            }

    def _categorize_semver(self) -> None:
        unsorted = [x for x in list(self._images.values()) if x is not None]
        # Add a single semver tag to each image
        for img in unsorted:
            if img.tags:
                semvers = [semver.Version.parse(t) for t in img.tags]
                semvers.sort()
                if len(semvers) > 0:
                    img.semver_tag = semvers[0]
                else:
                    img.semver_tag = semver.Version.parse(
                        f"0.0.0-{img.digest}"
                    )
            else:
                img.semver_tag = semver.Version.parse(f"0.0.0-{img.digest}")
        sorted_img = sorted(unsorted, reverse=True)
        self._categorized_images.semver = {x.digest: x for x in sorted_img}

    def _categorize_untagged(self) -> None:
        untagged = self._find_untagged_images()
        self._categorized_images.untagged = {
            x.digest: x for x in sorted(list(untagged.values()), reverse=True)
        }

    def _canonicalize_image_map(self, inp: ImageSpec) -> dict[str, Image]:
        """Take any of the ways of specifying images (dict of digest to
        Image, list of Images, list of digests, or single digest or Image)
        and return the dict mapping digest to Image.
        """
        # It's already in canonical form
        if isinstance(inp, dict):
            return inp

        # It's empty
        if not inp:
            return {}

        if isinstance(inp, list):
            item = inp[0]
            # List of digests
            if isinstance(item, str):
                # They better not be mixed.
                imgstrs = cast(list[str], inp)
                return {x: self._images[x] for x in imgstrs}
            # List of Images
            imgs = cast(list[Image], inp)
            return {x.digest: x for x in imgs}

        # Single items
        # Digest
        if isinstance(inp, str):
            return {inp: self._images[inp]}
        # Image
        return {inp.digest: inp}
