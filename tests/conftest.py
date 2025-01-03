"""Test fixtures for registry image reaper."""

from pathlib import Path

import pytest

from rsp_reaper.config import KeepPolicy, RegistryConfig
from rsp_reaper.storage.dockerhub import DockerHubClient
from rsp_reaper.storage.gar import GARClient
from rsp_reaper.storage.ghcr import GhcrClient


@pytest.fixture
def gar_cfg() -> RegistryConfig:
    """Config for Google Artifact Registry."""
    input_file = Path(__file__).parent / "support" / "gar.contents.json"
    return RegistryConfig(
        category="pkg.dev",
        registry="https://us-central1-docker.pkg.dev",
        owner="rubin-shared-services-71ec",
        namespace="sciplat",
        repository="sciplat-lab",
        keep=KeepPolicy(),
        image_version_class="rsp",
        dry_run=True,
        debug=True,
        input_file=input_file,
    )


@pytest.fixture
def gar_client(gar_cfg: RegistryConfig) -> GARClient:
    """Client for Google Artifact Registry."""
    return GARClient(cfg=gar_cfg)


@pytest.fixture
def ghcr_cfg() -> RegistryConfig:
    """Config for GitHub Container Registry."""
    input_file = Path(__file__).parent / "support" / "ghcr.io.contents.json"
    return RegistryConfig(
        category="ghcr.io",
        registry="https://ghcr.io",
        owner="lsst-sqre",
        repository="sciplat-lab",
        keep=KeepPolicy(),
        image_version_class="rsp",
        dry_run=True,
        debug=True,
        input_file=input_file,
    )


@pytest.fixture
def ghcr_client(ghcr_cfg: RegistryConfig) -> GhcrClient:
    """Client for GitHub Container Registry."""
    return GhcrClient(cfg=ghcr_cfg)


@pytest.fixture
def dockerhub_cfg() -> RegistryConfig:
    """Config for DockerHub."""
    input_file = Path(__file__).parent / "support" / "docker.io.contents.json"
    return RegistryConfig(
        category="hub.docker.com",
        registry="https://docker.io",
        owner="lsstsqre",
        repository="sciplat-lab",
        keep=KeepPolicy(),
        image_version_class="rsp",
        dry_run=True,
        debug=True,
        input_file=input_file,
    )


@pytest.fixture
def dockerhub_client(dockerhub_cfg: RegistryConfig) -> DockerHubClient:
    """Client for Docker Hub."""
    return DockerHubClient(cfg=dockerhub_cfg)
