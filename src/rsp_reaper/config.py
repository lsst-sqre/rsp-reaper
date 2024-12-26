"""Configuration for the reaper."""

from dataclasses import dataclass

from .models.registry_category import RegistryCategory


@dataclass
class Auth:
    """Generic authentication item."""

    realm: str
    username: str
    password: str


@dataclass
class Config:
    """Top-level configuration item."""

    namespace: str
    repository: str
    registry: str
    project: str | None = None
    category: RegistryCategory
    auth: Auth | None = None
