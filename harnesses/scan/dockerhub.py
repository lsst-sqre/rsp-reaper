"""Interactive harness for Docker Hub."""

import os

from rsp_reaper.config import RegistryAuth, RegistryConfig, KeepPolicy
from rsp_reaper.storage.dockerhub import DockerHubClient

# We want to explode if the auth isn't set.
auth = RegistryAuth(
    username=os.environ["DOCKERHUB_USER"],
    password=os.environ["DOCKERHUB_PASSWORD"],
)
cfg = RegistryConfig(
    category="hub.docker.com",
    registry="https://docker.io",
    owner="lsstsqre",
    repository="sciplat-lab",
    keep=KeepPolicy(),
    debug=True,
    dry_run=True
)
c = DockerHubClient(cfg=cfg)
c.authenticate(auth)
c.scan_repo()
