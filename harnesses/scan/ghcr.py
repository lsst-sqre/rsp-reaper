"""Interactive harness for GitHub Container Registry."""

import os

from rsp_reaper.config import KeepPolicy, RegistryAuth, RegistryConfig
from rsp_reaper.storage.ghcr import GhcrClient

# We want to explode if the token isn't set.
auth = RegistryAuth(password=os.environ["GHCR_TOKEN"])
cfg = RegistryConfig(
    category="ghcr.io",
    registry="https://ghcr.io",
    owner="lsst-sqre",
    repository="sciplat-lab",
    keep=KeepPolicy(),
    dry_run=True,
)
c = GhcrClient(cfg=cfg)
c.authenticate(auth)
c.scan_repo()
