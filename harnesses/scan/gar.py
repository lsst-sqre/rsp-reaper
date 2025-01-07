"""Interactive harness for Google Artifact Registry."""

from pydantic import HttpUrl

from rsp_reaper.config import KeepPolicy, RegistryConfig
from rsp_reaper.models.registry_category import RegistryCategory
from rsp_reaper.storage.gar import GARClient

cfg = RegistryConfig(
    category=RegistryCategory.GAR,
    registry=HttpUrl("https://us-central1-docker.pkg.dev"),
    owner="rubin-shared-services-71ec",
    namespace="sciplat",
    repository="sciplat-lab",
    keep=KeepPolicy(),
    dry_run=True,
    debug=True,
)
c = GARClient(cfg=cfg)
# No authentication; set up application default credentials in the environment
c.scan_repo()
