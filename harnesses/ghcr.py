import os

from rsp_reaper.storage.ghcr import GhcrClient

# We want to explode if the token isn't set.
token = os.environ["GHCR_TOKEN"]
c = GhcrClient(namespace="lsst-sqre", repository="sciplat-lab")
c.authenticate(token=token)
c.scan_repo()
