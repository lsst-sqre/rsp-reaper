"""Interactive harness for Google Artifact Registry."""

from rsp_reaper.storage.gar import GARClient

c = GARClient(
    location="us-central1",
    project_id="rubin-shared-services-71ec",
    repository="sciplat",
    image="sciplat-lab",
)
c.scan_repo()
