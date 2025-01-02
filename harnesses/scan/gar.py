"""Interactive harness for Google Artifact Registry."""

from rsp_reaper.config import KeepPolicy, RegistryConfig
from rsp_reaper.storage.gar import GARClient

cfg = RegistryConfig(
    category="pkg.dev",
    registry="https://us-central1-docker.pkg.dev",
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
