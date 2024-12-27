"""Configuration for a reaper for a particular container registry."""

from dataclasses import dataclass

from .models.registry_category import RegistryCategory


@dataclass
class RegistryAuth:
    """Generic authentication item for a container registry."""

    realm: str
    username: str
    password: str


@dataclass
class ContainerRegistryConfig:
    """Configuration for a particular container registry."""

    namespace: str
    repository: str
    registry: str
    category: RegistryCategory
    project: str | None = None
    auth: RegistryAuth | None = None
