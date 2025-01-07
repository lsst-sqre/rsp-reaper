"""Interactive harness for Docker Hub."""

import os

from pydantic import HttpUrl

from rsp_reaper.config import KeepPolicy, RegistryAuth, RegistryConfig
from rsp_reaper.models.registry_category import RegistryCategory
from rsp_reaper.storage.dockerhub import DockerHubClient

# We want to explode if the auth isn't set.
auth = RegistryAuth(
    username=os.environ["DOCKERHUB_USER"],
    password=os.environ["DOCKERHUB_PASSWORD"],
)
cfg = RegistryConfig(
    category=RegistryCategory.DOCKERHUB,
    registry=HttpUrl("https://docker.io"),
    owner="lsstsqre",
    repository="sciplat-lab",
    keep=KeepPolicy(),
    debug=True,
    dry_run=True,
)
c = DockerHubClient(cfg=cfg)
c.authenticate(auth)
c.scan_repo()
