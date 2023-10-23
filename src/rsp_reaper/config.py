from .models.registry_category import RegistryCategory
from dataclasses import dataclass, field


@dataclass
class Config:
    namespace: str
    repository: str
    registry: str
    project: str | None = None
    category: RegistryCategory
    auth: Auth | None = None


@dataclass
class Auth:
    realm: str
    username: str
    password: str
