"""Interactive harness for Google Artifact Registry."""

from pathlib import Path

from pydantic import HttpUrl
from safir.datetime import parse_timedelta as pt

from rsp_reaper.config import (
    IndividualKeepPolicy,
    KeepPolicy,
    RegistryConfig,
    RSPKeepers,
)
from rsp_reaper.models.registry_category import RegistryCategory
from rsp_reaper.services.reaper import Reaper

input_file = (
    Path(__file__).parent.parent.parent
    / "tests"
    / "support"
    / "docker.io.contents.json"
)

kp = KeepPolicy(
    untagged=IndividualKeepPolicy(number=0),
    semver=None,
    rsp=RSPKeepers(
        release=IndividualKeepPolicy(age=pt("2y")),
        weekly=IndividualKeepPolicy(number=78),
        daily=IndividualKeepPolicy(number=25),
        experimental=IndividualKeepPolicy(age=pt("30d")),
        unknown=IndividualKeepPolicy(age=pt("0s")),
    ),
)

cfg = RegistryConfig(
    category=RegistryCategory.DOCKERHUB,
    registry=HttpUrl("https://docker.io"),
    owner="lsstsqre",
    repository="sciplat-lab",
    dry_run=True,
    debug=True,
    input_file=input_file,
    keep=kp,
    image_version_class="rsp",
)

r = Reaper(cfg=cfg)
r.populate()
r.plan()
r.report()
