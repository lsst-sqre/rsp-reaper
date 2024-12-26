"""Interactive harness for Docker Hub."""

import os

from rsp_reaper.storage.dockerhub import DockerHubClient

# We want to explode if the auth isn't set.
username = os.environ["DOCKERHUB_USER"]
password = os.environ["DOCKERHUB_PASSWORD"]
c = DockerHubClient(namespace="lsstsqre", repository="sciplat-lab")
c.authenticate(username=username, password=password)
c.scan_repo()
