"""Tests for image comparison and sorting."""

from rsp_reaper.models.image import ImageVersionClass
from rsp_reaper.storage.gar import GARClient


def test_image_sort(gar_client: GARClient) -> None:
    """Test image comparison and sorting."""
    gar_client.categorize(ImageVersionClass.RSP)
    rels = list(gar_client._categorized_images.rsp["release"].values())[:2]
    assert rels[0] > rels[1]

    
