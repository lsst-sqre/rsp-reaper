"""Interactive harness for Google Artifact Registry."""

from pathlib import Path

from pydantic import HttpUrl

from rsp_reaper.config import KeepPolicy, RegistryConfig
from rsp_reaper.registry_category import RegistryCategory
from rsp_reaper.storage.gar import GARClient

input_file = (
    Path(__file__).parent.parent.parent
    / "tests"
    / "support"
    / "gar.contents.json"
)

cfg = RegistryConfig(
    category=RegistryCategory.GAR,
    registry=HttpUrl("https://us-central1-docker.pkg.dev"),
    owner="rubin-shared-services-71ec",
    namespace="sciplat",
    repository="sciplat-lab",
    dry_run=True,
    debug=True,
    input_file=input_file,
    keep=KeepPolicy(),
    image_version_class="rsp",
)

c = GARClient(cfg=cfg)
c.categorize()
