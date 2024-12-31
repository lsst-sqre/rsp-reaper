"""Test fixtures for registry image reaper."""

from pathlib import Path

import pytest

from rsp_reaper.config import KeepPolicy, RegistryConfig
from rsp_reaper.storage.dockerhub import DockerHubClient
from rsp_reaper.storage.gar import GARClient
from rsp_reaper.storage.ghcr import GhcrClient


@pytest.fixture
def gar_client() -> GARClient:
    """Client for Google Artifact Registry."""
    input_file = Path(__file__).parent / "support" / "gar.contents.json"
    cfg = RegistryConfig(
        category="pkg.dev",
        registry="https://us-central1-docker.pkg.dev",
        owner="rubin-shared-services-71ec",
        namespace="sciplat",
        repository="sciplat-lab",
        keep=KeepPolicy(),
        dry_run=True,
        debug=True,
        input_file=input_file,
    )
    return GARClient(cfg=cfg)


def ghcr_client() -> GhcrClient:
    """Client for GitHub Container Registry."""
    input_file = Path(__file__).parent / "support" / "ghcr.io.contents.json"
    cfg = RegistryConfig(
        category="ghcr.io",
        registry="https://ghcr.io",
        owner="lsst-sqre",
        repository="sciplat-lab",
        keep=KeepPolicy(),
        dry_run=True,
        debug=True,
        input_file=input_file,
    )
    return GhcrClient(cfg=cfg)


def dockerhub_client() -> DockerHubClient:
    """Client for Docker Hub."""
    input_file = Path(__file__).parent / "support" / "docker.io.contents.json"
    cfg = RegistryConfig(
        category="hub.docker.com",
        registry="https://docker.io",
        owner="lsstsqre",
        repository="sciplat-lab",
        keep=KeepPolicy(),
        dry_run=True,
        debug=True,
        input_file=input_file,
    )
    return DockerHubClient(cfg=cfg)
