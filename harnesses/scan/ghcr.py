"""Interactive harness for GitHub Container Registry."""

import os

from pydantic import HttpUrl

from rsp_reaper.config import KeepPolicy, RegistryAuth, RegistryConfig
from rsp_reaper.models.registry_category import RegistryCategory
from rsp_reaper.storage.ghcr import GhcrClient

# We want to explode if the token isn't set.
auth = RegistryAuth(password=os.environ["GHCR_TOKEN"])
cfg = RegistryConfig(
    category=RegistryCategory.GHCR,
    registry=HttpUrl("https://ghcr.io"),
    owner="lsst-sqre",
    repository="sciplat-lab",
    keep=KeepPolicy(),
    dry_run=True,
)
c = GhcrClient(cfg=cfg)
c.authenticate(auth)
c.scan_repo()
