"""Interactive harness for Google Artifact Registry."""
from pathlib import Path
from rsp_reaper.config import KeepPolicy, RegistryConfig
from rsp_reaper.models.image import ImageVersionClass
from rsp_reaper.storage.gar import GARClient

input_file = ( Path(__file__).parent.parent.parent / "tests" / "support" /
               "gar.contents.json")

cfg = RegistryConfig(
    category="pkg.dev",
    registry="https://us-central1-docker.pkg.dev",
    owner="rubin-shared-services-71ec",
    namespace="sciplat",
    repository="sciplat-lab",
    dry_run=True,
    debug=True,
    input_file=input_file,
    keep = KeepPolicy()
)

c = GARClient(cfg=cfg)
c.categorize(ImageVersionClass.RSP)



